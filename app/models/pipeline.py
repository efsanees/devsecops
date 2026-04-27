from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class Pipeline(Base):
    """
    Üretilen her CI/CD YAML pipeline'ını saklar.
    analysis_id — eğer /full veya /auto-push'tan üretildiyse ilgili Analysis kaydına FK.
    """

    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    repo_url = Column(String, index=True, nullable=False)
    yaml_content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
