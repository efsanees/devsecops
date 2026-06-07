import logging
import re
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.database import get_db
from app.models.job import Job

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


@router.get("/")
def home():
    return {"message": "DevSecOps AI calisiyor", "platforms": list(_VALID_PLATFORMS)}


# ── Job-based endpoints (multi-agent orchestrator) ───────────────────────────
# POST /job → anında job_id döner, arka planda orchestrator çalışır.
# Frontend job_id ile /ws/{job_id}'ye bağlanıp canlı ilerleme izler.


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
    """Job sonucundan Markdown rapor üretir ve indirir."""
    from app.reports.markdown_export import render_markdown

    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Job bulunamadı"})
    if job.status != "completed" or not job.result:
        raise HTTPException(status_code=409, detail={"code": "NOT_READY", "message": "Analiz henüz tamamlanmadı"})

    md = render_markdown(job.result)
    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=devsecops-report-{job_id[:8]}.md"},
    )


@router.get("/job/{job_id}/report.pdf")
def get_job_report_pdf(job_id: str, db: Session = Depends(get_db)):
    """
    Job sonucundan PDF rapor üretir.
    WeasyPrint kuruluysa PDF, kurulu değilse HTML döner (browser'dan yazdırılabilir).
    """
    from app.reports.pdf_export import render_pdf

    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Job bulunamadı"})
    if job.status != "completed" or not job.result:
        raise HTTPException(status_code=409, detail={"code": "NOT_READY", "message": "Analiz henüz tamamlanmadı"})

    content, is_pdf = render_pdf(job.result)
    if is_pdf:
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=devsecops-report-{job_id[:8]}.pdf"},
        )
    # WeasyPrint yoksa HTML döner — kullanıcı browser'dan PDF olarak kaydedebilir
    return Response(
        content=content,
        media_type="text/html",
        headers={"Content-Disposition": f"inline; filename=devsecops-report-{job_id[:8]}.html"},
    )


# ── Trend ve Karşılaştırma ───────────────────────────────────────────────────

@router.get("/jobs")
def get_jobs(limit: int = 30, db: Session = Depends(get_db)):
    """Son N analiz job'unu döner (History sayfası için)."""
    from app.services.trends_service import list_all_jobs
    return list_all_jobs(db, limit)


@router.get("/trends")
def get_trends(repo_url: str, db: Session = Depends(get_db)):
    """Aynı repo için zaman içindeki DSOMM skor değişimini döner."""
    from app.services.trends_service import list_jobs_for_repo
    if not _GITHUB_URL_RE.match(repo_url.strip()):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_URL", "message": "Gecerli bir GitHub repo URL'si girin."},
        )
    return list_jobs_for_repo(db, repo_url.strip().rstrip("/"))


@router.get("/compare")
def get_compare(job_a: str, job_b: str, db: Session = Depends(get_db)):
    """İki job arasındaki bulgu farkını (eklenen/düzeltilen) döner."""
    from app.services.trends_service import compare_jobs
    result = compare_jobs(db, job_a, job_b)
    if "error" in result:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": result["error"]})
    return result
