import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    # Yazma endpoint'lerini korumak için. Boşsa geliştirme modunda auth atlanır.
    API_KEY: str = os.getenv("API_KEY", "")

    def validate(self) -> None:
        """Uygulama başlangıcında zorunlu değişkenleri kontrol eder."""
        missing = []
        if not self.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        if missing:
            raise RuntimeError(
                f"Eksik zorunlu ortam değişkenleri: {', '.join(missing)}. "
                "Lütfen .env dosyanızı kontrol edin."
            )
        if not self.API_KEY:
            logger.warning(
                "API_KEY tanımlanmamış — /auto-push endpoint'i kimlik doğrulamasız çalışıyor. "
                "Üretim ortamı için .env'e API_KEY ekleyin."
            )


settings = Settings()
