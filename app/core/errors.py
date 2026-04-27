import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


def _error_body(code: str, message: str, details: list | None = None) -> dict:
    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    messages = []
    for e in exc.errors():
        field = " -> ".join(str(loc) for loc in e["loc"])
        messages.append(f"{field}: {e['msg']}")
    return JSONResponse(
        status_code=422,
        content=_error_body(
            code="VALIDATION_ERROR",
            message="İstek gövdesi geçersiz.",
            details=messages,
        ),
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "HTTP_ERROR")
        message = detail.get("message", str(detail))
    else:
        code = "HTTP_ERROR"
        message = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code=code, message=message),
    )


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=_error_body(
            code="RATE_LIMIT_EXCEEDED",
            message=(
                f"Çok fazla istek gönderildi (limit: {exc.detail}). "
                "Lütfen bir süre bekleyip tekrar deneyin."
            ),
        ),
    )


async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error(f"Beklenmedik hata [{request.method} {request.url.path}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=_error_body(
            code="INTERNAL_ERROR",
            message="Sunucu tarafında beklenmedik bir hata oluştu.",
        ),
    )
