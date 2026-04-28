"""
Secret Detection Agent — Gitleaks ile hardcoded credential taraması.

AWS key, GitHub token, Stripe key, private key, connection string
ve 150+ kural türünü tespit eder.

Güvenlik garantisi:
  - Secret değerleri hiçbir zaman tam olarak loglanmaz veya saklanmaz.
  - Findings'teki redacted_match: ilk 4 + "..." + son 4 karakter.
  - Docker container --redact flag ile çalışır.
"""

import asyncio
import logging
from collections import Counter

from app.agents.base import Agent, AgentResult
from app.security.runners import is_docker_available
from app.security.runners.gitleaks_runner import run_gitleaks
from app.utils.repo_downloader import download_repo

logger = logging.getLogger(__name__)


class SecretAgent(Agent):
    name = "secret_detection"

    async def run(self, state: dict) -> AgentResult:
        repo_url = state["repo_url"]
        token = state.get("token", "")

        logger.info("[SecretAgent] Başlıyor")

        if not is_docker_available():
            logger.warning("[SecretAgent] Docker mevcut değil, atlanıyor")
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={"skipped_reason": "Docker mevcut değil — Gitleaks Docker gerektirir"},
                findings=[],
            )

        repo_dir = state.get("temp_dir")
        base_dir = None
        if not repo_dir:
            logger.info("[SecretAgent] temp_dir yok, repo indiriliyor")
            repo_dir, base_dir = await asyncio.to_thread(download_repo, repo_url, token)

        try:
            findings = await asyncio.to_thread(run_gitleaks, repo_dir)

            # Secret türlerine göre grupla (AWS, GitHub, Stripe vb.)
            type_counts = Counter(f.get("secret_type", "Unknown") for f in findings)

            severity_counts = {"HIGH": 0, "MEDIUM": 0}
            for f in findings:
                sev = f.get("severity", "MEDIUM")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            # Entropy'ye göre sırala — en riskli önce
            findings.sort(key=lambda f: f.get("entropy", 0), reverse=True)

            logger.info(
                "[SecretAgent] Tamamlandı: %d bulgu — türler: %s",
                len(findings),
                dict(type_counts),
            )

            return AgentResult(
                agent_name=self.name,
                success=True,
                data={
                    "total_count": len(findings),
                    "severity_counts": severity_counts,
                    "secret_type_counts": dict(type_counts),
                },
                findings=findings,
            )

        finally:
            if base_dir:
                import shutil
                shutil.rmtree(base_dir, ignore_errors=True)
