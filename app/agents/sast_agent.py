"""
SAST Agent — Bandit (Python) + Semgrep (çok dilli) birleşik statik analiz.

Akış:
  1. state["temp_dir"] varsa kullan, yoksa repoyu ZIP'ten indir.
  2. Bandit'i Python dosyaları üzerinde çalıştır (Docker gerektirmez).
  3. Semgrep'i tüm repo üzerinde Docker'da çalıştır.
  4. İki sonucu dedupe ederek birleştir.
  5. AgentResult döndür.

Dedupe kuralı: aynı (file, line) çiftine sahip bulgu iki araçtan geliyorsa
Semgrep'inkini tercih et (daha zengin metadata), Bandit'inkini at.
"""

import asyncio
import logging
import shutil

from app.agents.base import Agent, AgentResult
from app.scoring.cwe_owasp_mapper import enrich_finding
from app.security.runners import is_docker_available
from app.security.runners.semgrep_runner import run_semgrep
from app.security.sast_analyzer import run_bandit_on_dir
from app.utils.repo_downloader import download_repo

logger = logging.getLogger(__name__)

# Bandit bulguları için ortak şemaya dönüştürme
_BANDIT_OWASP: dict[str, str] = {
    "B101": "A05:2021",   # assert kullanımı
    "B102": "A01:2021",   # exec kullanımı
    "B103": "A01:2021",   # dosya izinleri
    "B104": "A01:2021",   # bağlama 0.0.0.0
    "B105": "A07:2021",   # hardcoded password
    "B106": "A07:2021",   # hardcoded password fonksiyon argümanı
    "B107": "A07:2021",   # hardcoded password default arg
    "B108": "A01:2021",   # geçici dosya
    "B201": "A03:2021",   # Flask debug=True
    "B301": "A08:2021",   # pickle
    "B302": "A08:2021",   # marshal
    "B303": "A02:2021",   # MD5/SHA1
    "B304": "A02:2021",   # zayıf şifreleme
    "B305": "A02:2021",   # zayıf şifreleme modu
    "B306": "A02:2021",   # mktemp
    "B307": "A03:2021",   # eval
    "B308": "A03:2021",   # mark_safe
    "B310": "A10:2021",   # urllib open
    "B311": "A02:2021",   # random
    "B312": "A10:2021",   # telnetlib
    "B314": "A03:2021",   # XML ElementTree
    "B318": "A03:2021",   # XML DOM
    "B320": "A03:2021",   # lxml
    "B321": "A10:2021",   # FTP
    "B322": "A03:2021",   # input (Python 2)
    "B323": "A02:2021",   # unverified context
    "B324": "A02:2021",   # hashlib zayıf
    "B401": "A10:2021",   # import telnetlib
    "B402": "A10:2021",   # import ftplib
    "B403": "A08:2021",   # import pickle
    "B404": "A01:2021",   # import subprocess
    "B405": "A03:2021",   # import xml.etree
    "B501": "A02:2021",   # SSL verify=False
    "B502": "A02:2021",   # SSL eski versiyon
    "B503": "A02:2021",   # SSL zayıf cipher
    "B504": "A02:2021",   # SSL eski protokol
    "B505": "A02:2021",   # zayıf kriptografik anahtar
    "B506": "A03:2021",   # yaml.load unsafe
    "B601": "A01:2021",   # paramiko shell
    "B602": "A01:2021",   # subprocess shell=True
    "B603": "A01:2021",   # subprocess
    "B604": "A01:2021",   # shell fonksiyon
    "B605": "A01:2021",   # os.system
    "B606": "A01:2021",   # os.popen
    "B607": "A01:2021",   # partial executable
    "B608": "A03:2021",   # SQL injection
    "B609": "A01:2021",   # wildcard injection
    "B610": "A03:2021",   # Django extra
    "B611": "A03:2021",   # Django RawSQL
    "B701": "A03:2021",   # jinja2 autoescape
    "B702": "A03:2021",   # use of mako
    "B703": "A03:2021",   # Django mark_safe
}


def _normalize_bandit(finding: dict) -> dict:
    rule_id = finding.get("issue_id", "")
    return {
        "source": "bandit",
        "type": "SAST",
        "rule_id": rule_id,
        "severity": finding.get("severity", "MEDIUM"),
        "file": finding.get("file", ""),
        "line": finding.get("line"),
        "message": finding.get("summary", ""),
        "owasp_category": _BANDIT_OWASP.get(rule_id),
        "fix": None,
    }


def _dedupe(bandit: list[dict], semgrep: list[dict]) -> list[dict]:
    """
    Aynı (file, line) çiftinde iki araç da bulgu verirse Semgrep'i tercih et.
    """
    semgrep_keys = {(f["file"], f["line"]) for f in semgrep}
    deduped_bandit = [
        f for f in bandit
        if (f["file"], f["line"]) not in semgrep_keys
    ]
    return semgrep + deduped_bandit


class SASTAgent(Agent):
    name = "sast"

    async def run(self, state: dict) -> AgentResult:
        repo_url = state["repo_url"]
        token = state.get("token", "")

        logger.info("[SAST] Başlıyor")

        # Repo dizinini al (orchestrator zaten indirdiyse kullan)
        repo_dir = state.get("temp_dir")
        base_dir = None
        if not repo_dir:
            logger.info("[SAST] temp_dir yok, repo indiriliyor")
            repo_dir, base_dir = await asyncio.to_thread(download_repo, repo_url, token)

        try:
            # 1. Bandit (sync, thread pool'da)
            logger.info("[SAST] Bandit çalıştırılıyor")
            raw_bandit = await asyncio.to_thread(run_bandit_on_dir, repo_dir)
            bandit_findings = [_normalize_bandit(f) for f in raw_bandit]
            logger.info("[SAST] Bandit: %d bulgu", len(bandit_findings))

            # 2. Semgrep (Docker — sadece Docker müsaitse)
            semgrep_findings: list[dict] = []
            if is_docker_available():
                logger.info("[SAST] Semgrep çalıştırılıyor (Docker)")
                semgrep_findings = await asyncio.to_thread(run_semgrep, repo_dir)
                logger.info("[SAST] Semgrep: %d bulgu", len(semgrep_findings))
            else:
                logger.warning("[SAST] Docker mevcut değil, Semgrep atlandı")

            # 3. Dedupe ve birleştir, CWE/OWASP zenginleştir
            all_findings = [enrich_finding(f) for f in _dedupe(bandit_findings, semgrep_findings)]

            severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for f in all_findings:
                sev = f.get("severity", "LOW")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            logger.info(
                "[SAST] Tamamlandı: %d toplam bulgu (H:%d M:%d L:%d)",
                len(all_findings),
                severity_counts["HIGH"],
                severity_counts["MEDIUM"],
                severity_counts["LOW"],
            )

            return AgentResult(
                agent_name=self.name,
                success=True,
                data={
                    "bandit_count": len(bandit_findings),
                    "semgrep_count": len(semgrep_findings),
                    "total_count": len(all_findings),
                    "severity_counts": severity_counts,
                    "docker_available": is_docker_available(),
                },
                findings=all_findings,
            )

        finally:
            # Eğer bu agent indirdiyse temizle (orchestrator indirdiyse o temizler)
            if base_dir:
                import shutil
                shutil.rmtree(base_dir, ignore_errors=True)
