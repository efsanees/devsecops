from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.types import JSON

from app.database import Base


class Analysis(Base):
    """
    Her /analyze, /full, /security çağrısının sonuçlarını tutar.
    security_summary — risk_reporter çıktısı (JSON)
    checks / issues  — compliance scoring çıktısı (JSON)
    """

    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String, index=True, nullable=False)
    language = Column(String, default="unknown")
    framework = Column(String, default="unknown")
    has_tests = Column(Boolean, default=False)
    has_docker = Column(Boolean, default=False)
    score = Column(Float, nullable=True)
    grade = Column(String(1), nullable=True)
    checks = Column(JSON, nullable=True)
    issues = Column(JSON, nullable=True)
    security_summary = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
