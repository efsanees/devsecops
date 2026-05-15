import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.routes import router
from app.api.ws import router as ws_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.errors import (
    validation_exception_handler,
    http_exception_handler,
    rate_limit_exceeded_handler,
    general_exception_handler,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    from app.database import init_db
    init_db()
    logger.info("DevSecOps AI baslatildi")
    yield
    logger.info("DevSecOps AI kapatildi")


app = FastAPI(
    title="DevSecOps AI",
    description=(
        "GitHub repolarını analiz eden, güvenlik açıklarını tespit eden ve "
        "projeye özel CI/CD pipeline üreten multi-agent DevSecOps asistanı.\n\n"
        "**Akış:** `POST /job` → WebSocket `/ws/{job_id}` → `GET /job/{job_id}`"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — dev (Vite:5173) + Docker (nginx:80) + env'den ek origin
import os as _os
_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:80",
    "http://localhost",
    "http://127.0.0.1",
]
_extra = [o.strip() for o in _os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
_origins = list(dict.fromkeys(_default_origins + _extra))  # dedupe, sıra korur

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.include_router(router)
app.include_router(ws_router)
