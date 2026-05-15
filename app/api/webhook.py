"""
GitHub Webhook endpoint — PR açıldığında/güncellendiğinde güvenlik analizi başlatır.

Kurulum (GitHub repo ayarları):
  Settings → Webhooks → Add webhook
    Payload URL : https://yourdomain.com/webhook/github
    Content type: application/json
    Secret      : GITHUB_WEBHOOK_SECRET (env değişkeniyle aynı)
    Events      : Pull requests

Güvenlik: X-Hub-Signature-256 başlığı HMAC-SHA256 ile doğrulanır.
GITHUB_WEBHOOK_SECRET tanımlı değilse webhook DEVRE DIŞI (güvensiz).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = logging.getLogger(__name__)


def _verify_signature(payload: bytes, signature_header: str | None) -> bool:
    """GitHub'ın gönderdiği HMAC-SHA256 imzasını doğrular."""
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        logger.warning("[Webhook] GITHUB_WEBHOOK_SECRET tanımlı değil — imza doğrulaması atlandı")
        return True  # Geliştirme ortamı için geçici tolerans

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


async def _handle_pr_event(payload: dict) -> None:
    """PR opened/synchronize event işleyicisi (BackgroundTask olarak çalışır)."""
    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        logger.debug("[Webhook] İlgisiz PR aksiyonu: %s", action)
        return

    pr        = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})

    owner      = repo_data.get("owner", {}).get("login", "")
    repo       = repo_data.get("name", "")
    repo_url   = repo_data.get("html_url", "")
    pr_number  = pr.get("number")
    head_sha   = pr.get("head", {}).get("sha", "")
    token      = ""   # Kullanıcı token'ı webhook'ta gelmiyor; public repo için gerek yok

    github_token = os.environ.get("GITHUB_TOKEN", "")

    if not owner or not repo or not pr_number:
        logger.error("[Webhook] Eksik PR verisi: owner=%s, repo=%s, pr=%s", owner, repo, pr_number)
        return

    logger.info("[Webhook] PR review başlıyor: %s/%s #%d", owner, repo, pr_number)

    try:
        from app.services.pr_review_service import run_pr_review
        result = await run_pr_review(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            head_sha=head_sha,
            repo_url=repo_url,
            token=token,
            github_token=github_token,
        )
        logger.info("[Webhook] PR review tamamlandı: %s", result)
    except Exception as exc:
        logger.error("[Webhook] PR review hatası: %s", exc, exc_info=True)


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    GitHub webhook receiver.

    Desteklenen event'ler:
      - pull_request (opened, synchronize, reopened)
      - ping (bağlantı testi)
    """
    payload_bytes = await request.body()
    signature     = request.headers.get("X-Hub-Signature-256")
    event_type    = request.headers.get("X-GitHub-Event", "")

    # İmza doğrulama
    if not _verify_signature(payload_bytes, signature):
        logger.warning("[Webhook] Geçersiz imza — istek reddedildi")
        raise HTTPException(status_code=401, detail="Geçersiz webhook imzası")

    # Ping event — bağlantı testi
    if event_type == "ping":
        return {"message": "pong", "status": "DevSecOps AI webhook aktif"}

    # PR event
    if event_type != "pull_request":
        return {"message": f"'{event_type}' event'i yoksayıldı", "status": "ok"}

    import json
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Geçersiz JSON")

    # BackgroundTask olarak işle — anında 200 döner
    background_tasks.add_task(_handle_pr_event, payload)

    return {
        "status": "accepted",
        "pr":     payload.get("pull_request", {}).get("number"),
        "action": payload.get("action"),
    }
