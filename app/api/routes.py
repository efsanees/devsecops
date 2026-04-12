import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.analyzer.repo_analyzer import analyze_repo
from app.generator.pipeline_generator import generate_pipeline
from app.github.github_service import get_all_files, get_repo_files, push_to_github
from app.scoring.scoring import calculate_score
from app.utils.yaml_utils import ensure_trivy, filter_context

logger = logging.getLogger(__name__)

router = APIRouter()


class RepoRequest(BaseModel):
    repo_url: str
    token: str = ""


def _get_context(repo_url: str, token: str) -> list:
    all_files = get_all_files(repo_url, token)
    if not all_files:
        root = get_repo_files(repo_url, token)
        if isinstance(root, list):
            all_files = [f.get("path", f.get("name", "")) for f in root]
    return filter_context(all_files)  # medya dosyaları temizlendi, limit uygulandı


@router.get("/")
def home():
    return {"message": "DevSecOps AI çalışıyor"}


@router.post("/analyze")
def analyze(body: RepoRequest):
    # Token log'a düşmüyor
    logger.info(f"/analyze çağrıldı: {body.repo_url}")
    return analyze_repo(body.repo_url, body.token)


@router.post("/auto")
def auto(body: RepoRequest):
    logger.info(f"/auto çağrıldı: {body.repo_url}")
    analysis = analyze_repo(body.repo_url, body.token)
    context = _get_context(body.repo_url, body.token)

    yaml_text = generate_pipeline(analysis, context)
    yaml_text = ensure_trivy(yaml_text)

    return {"pipeline": yaml_text}


@router.post("/auto-push")
def auto_push(body: RepoRequest):
    if not body.token:
        raise HTTPException(status_code=400, detail="auto-push için GitHub token zorunludur")

    logger.info(f"/auto-push çağrıldı: {body.repo_url}")
    analysis = analyze_repo(body.repo_url, body.token)
    context = _get_context(body.repo_url, body.token)

    yaml_text = generate_pipeline(analysis, context)
    yaml_text = ensure_trivy(yaml_text)

    result = push_to_github(body.repo_url, body.token, yaml_text)

    return {"pipeline": yaml_text, "github_response": result}


@router.post("/full")
def full(body: RepoRequest):
    logger.info(f"/full çağrıldı: {body.repo_url}")

    analysis = analyze_repo(body.repo_url, body.token)
    context = _get_context(body.repo_url, body.token)

    yaml_text = generate_pipeline(analysis, context)
    yaml_text = ensure_trivy(yaml_text)

    scoring = calculate_score(analysis, yaml_text)

    # Standardize edilmiş response
    return {
        "analysis": analysis,
        "pipeline": yaml_text,
        "score": scoring["score"],
        "grade": scoring["grade"],
        "issues": scoring["issues"],
        "checks": scoring["checks"]
    }
