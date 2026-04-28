import logging
import re
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
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
from app.models.job import Job
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


# ── Job-based endpoints (multi-agent orchestrator) ────────────────────────────
#
# Bu endpoint'ler eski /full ve /security'nin async versiyonu.
# POST /job → anında job_id döner, arka planda orchestrator çalışır.
# Frontend job_id ile /ws/{job_id}'ye bağlanıp canlı ilerleme izler.
# Eski endpoint'ler backward compat için korunuyor.


@router.post("/job", status_code=202)
@limiter.limit("10/minute")
async def start_job(
    request: Request,
    body: RepoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Multi-agent analizi başlatır.
    Anında job_id döner (202 Accepted), analiz arka planda çalışır.
    İlerlemeyi ws://.../ws/{job_id} üzerinden izleyebilirsin.
    """
    from app.orchestrator import Orchestrator

    job_id = str(uuid.uuid4())
    job = Job(id=job_id, repo_url=body.repo_url, platform=body.platform, status="pending")
    db.add(job)
    db.commit()

    orchestrator = Orchestrator()
    background_tasks.add_task(
        orchestrator.run, job_id, body.repo_url, body.token, body.platform
    )

    logger.info("/job başlatıldı: %s → job_id=%s", body.repo_url, job_id)
    return {
        "job_id": job_id,
        "status": "pending",
        "ws_url": f"/ws/{job_id}",
    }


@router.get("/job/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Job durumunu ve (tamamlandıysa) sonucunu döner."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Job bulunamadı"},
        )
    return {
        "job_id": job.id,
        "status": job.status,
        "repo_url": job.repo_url,
        "platform": job.platform,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "result": job.result,   # None iken hâlâ çalışıyor
        "error": job.error,
    }


@router.get("/job/{job_id}/yaml")
def get_job_yaml(job_id: str, db: Session = Depends(get_db)):
    """Üretilen pipeline YAML'ını plain text olarak döner (indirilebilir)."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Job bulunamadı"})
    if job.status != "completed" or not job.result:
        raise HTTPException(status_code=409, detail={"code": "NOT_READY", "message": "Analiz henüz tamamlanmadı"})

    yaml_content = job.result.get("pipeline_yaml", "")
    if not yaml_content:
        raise HTTPException(status_code=404, detail={"code": "NO_YAML", "message": "Pipeline YAML bulunamadı"})

    return Response(
        content=yaml_content,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=pipeline.yml"},
    )


@router.get("/job/{job_id}/report.md")
def get_job_report_md(job_id: str, db: Session = Depends(get_db)):
    """Markdown rapor — Gün 11'de implement edilecek, şimdilik stub."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Job bulunamadı"})
    if job.status != "completed":
        raise HTTPException(status_code=409, detail={"code": "NOT_READY", "message": "Analiz henüz tamamlanmadı"})
    # TODO: Gün 11'de app.reports.markdown_export.render_markdown(job.result) çağrılacak
    return Response(
        content=f"# DevSecOps Raporu\n\nJob: {job_id}\nDurum: {job.status}\n",
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=report-{job_id[:8]}.md"},
    )


@router.get("/job/{job_id}/report.pdf")
def get_job_report_pdf(job_id: str, db: Session = Depends(get_db)):
    """PDF rapor — Gün 11'de implement edilecek, şimdilik stub."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Job bulunamadı"})
    if job.status != "completed":
        raise HTTPException(status_code=409, detail={"code": "NOT_READY", "message": "Analiz henüz tamamlanmadı"})
    # TODO: Gün 11'de app.reports.pdf_export.render_pdf(job.result) çağrılacak
    raise HTTPException(
        status_code=501,
        detail={"code": "NOT_IMPLEMENTED", "message": "PDF export yakında aktif olacak"},
    )
