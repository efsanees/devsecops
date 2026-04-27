"""
Job ve AgentRun ORM modelleri — multi-agent analiz işlerinin yaşam döngüsü.

Job:      Bir analiz isteğini temsil eder. UUID tabanlı, durum makinesi var.
AgentRun: Bir Job içindeki tek bir agent çalışmasını temsil eder.
          Job'a foreign key ile bağlı — orchestrator her agent için bir kayıt açar.

Durum makinesi (Job.status):
    pending → running → completed
                      → failed
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.types import JSON

from app.database import Base


def _now():
    return datetime.now(timezone.utc)


def _new_uuid():
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=_new_uuid, index=True)
    repo_url = Column(String, nullable=False, index=True)

    # pending | running | completed | failed
    status = Column(String(16), nullable=False, default="pending", index=True)

    platform = Column(String(32), nullable=True)   # github_actions | gitlab_ci | jenkins

    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    # Orchestrator'ın topladığı nihai birleştirilmiş sonuç
    result = Column(JSON, nullable=True)

    # Hata mesajı (status == "failed" ise dolu)
    error = Column(Text, nullable=True)


class AgentRun(Base):
    """Bir Job içindeki tek bir agent çalışmasının kaydı."""

    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    agent_name = Column(String(64), nullable=False)

    # pending | running | completed | failed
    status = Column(String(16), nullable=False, default="pending")

    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Agent'ın döndürdüğü AgentResult.data ve AgentResult.findings
    data = Column(JSON, nullable=True)
    findings = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
