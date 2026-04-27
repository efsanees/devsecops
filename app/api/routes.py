import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.analyzer.repo_analyzer import analyze_repo
from app.generator.pipeline_generator import generate_pipeline
from app.github.github_service import (
    get_all_files, get_file_content, get_repo_files, push_to_github,
)
from app.scoring.scoring import calculate_score
from app.utils.yaml_utils import ensure_trivy, filter_context
from app.core.limiter import limiter
from app.core.security import require_api_key
from app.database import get_db
from app.models.analysis import Analysis as AnalysisModel
from app.models.pipeline import Pipeline as PipelineModel
from app.security.sca_analyzer import analyze_dependencies
from app.security.sast_analyzer import analyze_static
from app.security.risk_reporter import generate_risk_report

logger = logging.getLogger(__name__)
router = APIRouter()

_GITHUB_URL_RE = re.compile(
    r"^https://github\.com/[a-zA-Z0-9](?:[a-zA-Z0-9._-]{0,37}[a-zA-Z0-9])?/[a-zA-Z0-9._-]+/?$"
)
_VALID_PLATFORMS = {"github_actions", "gitlab_ci", "jenkins"}


class RepoRequest(BaseModel):
    repo_url: str
    token: str = ""
    platform: str = "github_actions"

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        v = v.strip()
        if not _GITHUB_URL_RE.match(v):
            raise ValueError("Gecerli bir GitHub repo URL'si girin. Ornek: https://github.com/owner/repo")
        return v.rstrip("/")

    @field_validator("token")
    @classmethod
    def strip_token(cls, v: str) -> str:
        return v.strip()

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v not in _VALID_PLATFORMS:
            raise ValueError(f"Platform '{v}' gecersiz. Gecerli: {_VALID_PLATFORMS}")
        return v


def _get_all_files_safe(repo_url: str, token: str) -> list:
    all_files = get_all_files(repo_url, token)
    if not all_files:
        root = get_repo_files(repo_url, token)
        if isinstance(root, list):
            all_files = [f.get("path", f.get("name", "")) for f in root]
    return all_files or []


def _get_context(repo_url: str, token: str) -> list:
    return filter_context(_get_all_files_safe(repo_url, token))


@router.get("/")
def home():
    return {"message": "DevSecOps AI calisiyor", "platforms": list(_VALID_PLATFORMS)}


@router.post("/analyze")
@limiter.limit("15/minute")
def analyze(request: Request, body: RepoRequest, db: Session = Depends(get_db)):
    logger.info(f"/analyze cagrild: {body.repo_url}")
    result = analyze_repo(body.repo_url, body.token)
    record = AnalysisModel(
        repo_url=body.repo_url,
        language=result.get("language"),
        framework=result.get("framework"),
        has_tests=result.get("has_tests"),
        has_docker=result.get("has_docker"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {**result, "analysis_id": record.id}


@router.post("/auto")
@limiter.limit("10/minute")
def auto(request: Request, body: RepoRequest, db: Session = Depends(get_db)):
    logger.info(f"/auto cagrild: {body.repo_url} [{body.platform}]")
    analysis = analyze_repo(body.repo_url, body.token)
    context = _get_context(body.repo_url, body.token)
    yaml_text = generate_pipeline(analysis, context, body.platform)
    if body.platform == "github_actions":
        yaml_text = ensure_trivy(yaml_text)
    a_record = AnalysisModel(
        repo_url=body.repo_url,
        language=analysis.get("language"),
        framework=analysis.get("framework"),
        has_tests=analysis.get("has_tests"),
        has_docker=analysis.get("has_docker"),
    )
    db.add(a_record)
    db.flush()
    p_record = PipelineModel(analysis_id=a_record.id, repo_url=body.repo_url, yaml_content=yaml_text)
    db.add(p_record)
    db.commit()
    return {
        "pipeline": yaml_text,
        "analysis_id": a_record.id,
        "platform": body.platform,
        "language": analysis.get("language"),
        "framework": analysis.get("framework"),
        "has_tests": analysis.get("has_tests"),
        "has_docker": analysis.get("has_docker"),
    }


@router.post("/auto-push")
@limiter.limit("5/minute")
def auto_push(
    request: Request,
    body: RepoRequest,
    _: None = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    if not body.token:
        raise HTTPException(
            status_code=400,
            detail={"code": "MISSING_TOKEN", "message": "auto-push icin GitHub token zorunludur."},
        )
    if body.platform != "github_actions":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_PLATFORM",
                "message": "auto-push yalnizca github_actions platformu icin destekleniyor.",
            },
        )
    logger.info(f"/auto-push cagrild: {body.repo_url}")
    analysis = analyze_repo(body.repo_url, body.token)
    context = _get_context(body.repo_url, body.token)
    yaml_text = ensure_trivy(generate_pipeline(analysis, context, "github_actions"))
    gh_response = push_to_github(body.repo_url, body.token, yaml_text)
    a_record = AnalysisModel(
        repo_url=body.repo_url,
        language=analysis.get("language"),
        framework=analysis.get("framework"),
        has_tests=analysis.get("has_tests"),
        has_docker=analysis.get("has_docker"),
    )
    db.add(a_record)
    db.flush()
    p_record = PipelineModel(analysis_id=a_record.id, repo_url=body.repo_url, yaml_content=yaml_text)
    db.add(p_record)
    db.commit()
    return {"pipeline": yaml_text, "github_response": gh_response, "analysis_id": a_record.id}


@router.post("/full")
@limiter.limit("10/minute")
def full(request: Request, body: RepoRequest, db: Session = Depends(get_db)):
    logger.info(f"/full cagrild: {body.repo_url} [{body.platform}]")
    analysis = analyze_repo(body.repo_url, body.token)
    context = _get_context(body.repo_url, body.token)
    yaml_text = generate_pipeline(analysis, context, body.platform)
    if body.platform == "github_actions":
        yaml_text = ensure_trivy(yaml_text)
    scoring = calculate_score(analysis, yaml_text, body.platform)
    a_record = AnalysisModel(
        repo_url=body.repo_url,
        language=analysis.get("language"),
        framework=analysis.get("framework"),
        has_tests=analysis.get("has_tests"),
        has_docker=analysis.get("has_docker"),
        score=scoring["score"],
        grade=scoring["grade"],
        checks=scoring["checks"],
        issues=scoring["issues"],
    )
    db.add(a_record)
    db.flush()
    p_record = PipelineModel(analysis_id=a_record.id, repo_url=body.repo_url, yaml_content=yaml_text)
    db.add(p_record)
    db.commit()
    return {
        "analysis_id": a_record.id,
        "analysis": analysis,
        "pipeline": yaml_text,
        "score": scoring["score"],
        "grade": scoring["grade"],
        "issues": scoring["issues"],
        "checks": scoring["checks"],
        "platform": body.platform,
    }


@router.post("/security")
@limiter.limit("10/minute")
def security(request: Request, body: RepoRequest, db: Session = Depends(get_db)):
    logger.info(f"/security cagrild: {body.repo_url}")
    analysis = analyze_repo(body.repo_url, body.token)
    all_files = _get_all_files_safe(body.repo_url, body.token)
    sast_result = analyze_static(
        body.repo_url, body.token, all_files,
        analysis.get("language", "unknown"), get_file_content,
    )
    sca_result = analyze_dependencies(body.repo_url, body.token, all_files, get_file_content)
    risk = generate_risk_report(sast_result, sca_result)
    a_record = AnalysisModel(
        repo_url=body.repo_url,
        language=analysis.get("language"),
        framework=analysis.get("framework"),
        has_tests=analysis.get("has_tests"),
        has_docker=analysis.get("has_docker"),
        security_summary=risk,
    )
    db.add(a_record)
    db.commit()
    db.refresh(a_record)
    return {
        "analysis_id": a_record.id,
        "repo_url": body.repo_url,
        "language": analysis.get("language"),
        "framework": analysis.get("framework"),
        "has_tests": analysis.get("has_tests"),
        "has_docker": analysis.get("has_docker"),
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "total_findings": risk["total_findings"],
        "by_severity": risk["by_severity"],
        "sast": risk["sast"],
        "sca": risk["sca"],
        "top_findings": risk["top_findings"],
    }


@router.get("/history")
def get_history(limit: int = 20, db: Session = Depends(get_db)):
    from sqlalchemy import desc
    records = (
        db.query(AnalysisModel)
        .order_by(desc(AnalysisModel.created_at))
        .limit(min(max(limit, 1), 100))
        .all()
    )
    return [
        {
            "id": r.id,
            "repo_url": r.repo_url,
            "language": r.language,
            "framework": r.framework,
            "score": r.score,
            "grade": r.grade,
            "risk_level": (r.security_summary or {}).get("risk_level"),
            "risk_score": (r.security_summary or {}).get("risk_score"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.get("/history/{analysis_id}")
def get_history_detail(analysis_id: int, db: Session = Depends(get_db)):
    record = db.query(AnalysisModel).filter(AnalysisModel.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Analiz bulunamadi"})
    return {
        "id": record.id,
        "repo_url": record.repo_url,
        "language": record.language,
        "framework": record.framework,
        "has_tests": record.has_tests,
        "has_docker": record.has_docker,
        "score": record.score,
        "grade": record.grade,
        "checks": record.checks,
        "issues": record.issues,
        "security_summary": record.security_summary,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
