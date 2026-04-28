"""
WebSocket endpoint ve JobEventBus.

JobEventBus:
  Her job_id için bir asyncio.Queue tutar.
  Orchestrator eventleri yayınlar, WebSocket handler okur.

  Neden asyncio.Queue:
    Hem publisher (orchestrator) hem consumer (WebSocket) aynı event
    loop içinde async çalışır — Queue thread-safe köprü görevi görür.

Event formatı:
  {
    "type":       "agent_started" | "agent_completed" | "agent_failed"
                  | "job_completed" | "job_failed" | "ping",
    "agent":      str (opsiyonel),
    "message":    str (opsiyonel),
    "timestamp":  float
  }
"""

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# job_id → asyncio.Queue
# Orchestrator event koyar, WebSocket handler okur.
_queues: dict[str, asyncio.Queue] = {}

HEARTBEAT_INTERVAL = 20   # saniye — bağlantı kopmalarını önler
QUEUE_TIMEOUT = 600       # saniye — job bu süreden uzun sürmemeli


# ── EventBus API (orchestrator tarafından çağrılır) ──────────────────────

def ensure_queue(job_id: str) -> asyncio.Queue:
    """Job başlarken queue oluşturur. Varsa mevcut döner."""
    if job_id not in _queues:
        _queues[job_id] = asyncio.Queue()
    return _queues[job_id]


async def publish(job_id: str, event: dict[str, Any]) -> None:
    """Orchestrator'dan event yayınlar. Queue yoksa sessizce geçer."""
    q = _queues.get(job_id)
    if q:
        event.setdefault("timestamp", time.time())
        await q.put(event)


def publish_sync(job_id: str, event: dict[str, Any]) -> None:
    """
    Sync context'ten (thread pool'dan) event yayınlamak için.
    asyncio.run_coroutine_threadsafe ile mevcut event loop'a gönderir.
    """
    try:
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(
            lambda: asyncio.ensure_future(publish(job_id, event))
        )
    except RuntimeError:
        pass  # Event loop kapalıysa sessizce geç


def close_queue(job_id: str) -> None:
    """Job bitince queue'yu serbest bırak."""
    _queues.pop(job_id, None)


# ── WebSocket endpoint ────────────────────────────────────────────────────

@router.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str) -> None:
    """
    Client job ilerlemesini bu endpoint üzerinden takip eder.

    Bağlantı:
      ws://localhost:8000/ws/{job_id}

    Mesaj tipleri (client'a giden):
      agent_started   → bir agent çalışmaya başladı
      agent_completed → agent başarıyla bitti
      agent_failed    → agent hata verdi
      job_completed   → tüm analiz tamamlandı
      job_failed      → analiz başarısız oldu
      ping            → heartbeat (bağlantı canlı tutma)
    """
    await websocket.accept()
    logger.info("[WS] Bağlandı: job_id=%s", job_id)

    q = ensure_queue(job_id)

    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_INTERVAL)
            except asyncio.TimeoutError:
                # Heartbeat gönder — bağlantıyı canlı tut
                await websocket.send_json({"type": "ping", "timestamp": time.time()})
                continue

            await websocket.send_json(event)

            # Terminal event: job bitti veya hata — bağlantıyı kapat
            if event.get("type") in ("job_completed", "job_failed"):
                break

    except WebSocketDisconnect:
        logger.info("[WS] Client bağlantıyı kesti: job_id=%s", job_id)
    except Exception as exc:
        logger.error("[WS] Hata: %s", exc)
    finally:
        close_queue(job_id)
        logger.info("[WS] Bağlantı kapandı: job_id=%s", job_id)
