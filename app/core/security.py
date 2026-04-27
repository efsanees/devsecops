from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Security(_api_key_header)) -> None:
    """
    /auto-push gibi yazma endpoint'leri için API key doğrulaması.
    API_KEY env değişkeni tanımlanmamışsa geliştirme modunda doğrulama atlanır.
    """
    if not settings.API_KEY:
        return
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": (
                    "Geçersiz veya eksik API anahtarı. "
                    "İstek başlığına 'X-API-Key' ekleyin."
                ),
            },
        )
