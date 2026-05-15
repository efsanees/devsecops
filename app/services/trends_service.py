"""
Trend ve karşılaştırma servisi.

list_jobs_for_repo: Aynı repo için tamamlanmış jobları zaman sırasıyla döner.
compare_jobs:       İki job arasındaki bulgu farkını (eklenen / düzeltilen) hesaplar.
"""

import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.job import Job


def _repo_hash(repo_url: str) -> str:
    return hashlib.sha256(repo_url.lower().strip("/").encode()).hexdigest()[:16]


def list_jobs_for_repo(db: Session, repo_url: str) -> list[dict]:
    """Aynı repo_url için tamamlanmış jobları eski→yeni sırasıyla döner."""
    jobs = (
        db.query(Job)
        .filter(Job.repo_url == repo_url, Job.status == "completed")
        .order_by(Job.finished_at)
        .all()
    )
    result = []
    for job in jobs:
        dsomm = (job.result or {}).get("dsomm", {})
        findings = (job.result or {}).get("findings", {})
        total_findings = (
            len(findings.get("sast") or [])
            + len(findings.get("sca") or [])
            + len(findings.get("secret") or [])
        )
        result.append({
            "job_id": job.id,
            "repo_url": job.repo_url,
            "platform": job.platform,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "dsomm_total": dsomm.get("total_score"),
            "dsomm_categories": dsomm.get("categories", {}),
            "total_findings": total_findings,
        })
    return result


def list_all_jobs(db: Session, limit: int = 30) -> list[dict]:
    """Son N tamamlanmış veya başarısız jobu döner (history sayfası için)."""
    jobs = (
        db.query(Job)
        .filter(Job.status.in_(["completed", "failed"]))
        .order_by(desc(Job.finished_at))
        .limit(min(max(limit, 1), 100))
        .all()
    )
    result = []
    for job in jobs:
        dsomm = (job.result or {}).get("dsomm", {})
        profile = (job.result or {}).get("profile", {})
        findings = (job.result or {}).get("findings", {})
        total_findings = (
            len(findings.get("sast") or [])
            + len(findings.get("sca") or [])
            + len(findings.get("secret") or [])
        )
        result.append({
            "job_id": job.id,
            "repo_url": job.repo_url,
            "platform": job.platform,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "dsomm_total": dsomm.get("total_score"),
            "language": profile.get("language"),
            "total_findings": total_findings,
            "error": job.error,
        })
    return result


def compare_jobs(db: Session, job_a_id: str, job_b_id: str) -> dict:
    """
    İki job arasındaki bulgu farkını hesaplar.
    Dönen dict:
      repo_match: iki job aynı repo mu
      job_a / job_b: özet bilgiler
      added:   B'de var A'da yok (yeni bulgular)
      removed: A'da var B'de yok (düzeltilen bulgular)
      unchanged_count: her ikisinde de var
      dsomm_diff: kategori bazlı DSOMM skor farkı (B - A)
    """
    job_a = db.get(Job, job_a_id)
    job_b = db.get(Job, job_b_id)

    if not job_a or not job_b:
        return {"error": "Job bulunamadı"}

    def _finding_key(f: dict) -> str:
        """Bulguyu benzersiz tanımlayan anahtar."""
        if f.get("type") == "SCA":
            return f"sca::{f.get('vuln_id','').upper()}::{f.get('package','').lower()}"
        return f"sast::{f.get('rule_id','')}-{f.get('file','')}-{f.get('line','')}"

    def _extract_findings(job: Job) -> dict[str, dict]:
        findings = (job.result or {}).get("findings", {})
        result = {}
        for category in ("sast", "sca", "secret"):
            for f in findings.get(category) or []:
                key = _finding_key(f)
                result[key] = {**f, "_category": category}
        return result

    fa = _extract_findings(job_a)
    fb = _extract_findings(job_b)

    keys_a = set(fa)
    keys_b = set(fb)

    added   = [fb[k] for k in (keys_b - keys_a)]
    removed = [fa[k] for k in (keys_a - keys_b)]
    unchanged_count = len(keys_a & keys_b)

    # DSOMM fark
    dsomm_a = (job_a.result or {}).get("dsomm", {})
    dsomm_b = (job_b.result or {}).get("dsomm", {})
    cats_a = dsomm_a.get("categories", {})
    cats_b = dsomm_b.get("categories", {})
    all_cats = set(cats_a) | set(cats_b)
    dsomm_diff = {
        cat: round((cats_b.get(cat, 0) or 0) - (cats_a.get(cat, 0) or 0), 2)
        for cat in all_cats
    }

    def _job_summary(job: Job, dsomm: dict) -> dict:
        profile = (job.result or {}).get("profile", {})
        return {
            "job_id": job.id,
            "repo_url": job.repo_url,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "dsomm_total": dsomm.get("total_score"),
            "total_findings": len(fa) if job is job_a else len(fb),
            "language": profile.get("language"),
        }

    return {
        "repo_match": job_a.repo_url == job_b.repo_url,
        "job_a": _job_summary(job_a, dsomm_a),
        "job_b": _job_summary(job_b, dsomm_b),
        "added": added,
        "removed": removed,
        "unchanged_count": unchanged_count,
        "dsomm_diff": dsomm_diff,
        "dsomm_total_diff": round(
            (dsomm_b.get("total_score") or 0) - (dsomm_a.get("total_score") or 0), 2
        ),
    }
