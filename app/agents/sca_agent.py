"""
SCA Agent — OSV.dev (ağ tabanlı) + Trivy (offline DB) bağımlılık analizi.

Akış:
  1. state["temp_dir"] varsa kullan, yoksa repo'yu indir.
  2. OSV.dev: bağımlılık dosyalarını okuyup batch API'ye sor.
  3. Trivy: Docker'da tüm repo üzerinde FS tarama yap.
  4. (vuln_id, package) bazlı dedupe — çakışmada "both" olarak işaretle.
  5. AgentResult döndür.

İki araç neden birlikte:
  OSV.dev → hızlı, ağ tabanlı, sadece lock/manifest bakar
  Trivy   → offline DB, binary tarama, IaC, daha kapsamlı ekosistem desteği
"""

import asyncio
import logging

from app.agents.base import Agent, AgentResult
from app.scoring.cwe_owasp_mapper import enrich_finding
from app.security.runners import is_docker_available
from app.security.runners.trivy_runner import run_trivy
from app.security.sca_analyzer import analyze_dependencies_from_dir
from app.utils.repo_downloader import download_repo

logger = logging.getLogger(__name__)


def _dedupe(osv: list[dict], trivy: list[dict]) -> list[dict]:
    """
    (vuln_id, package) bazlı dedupe.
    Her iki araç da aynı CVE'yi bulursa Trivy kaydı korunur, source="both" yapılır.
    """
    trivy_index: dict[tuple, dict] = {}
    for f in trivy:
        key = (f.get("vuln_id", "").upper(), f.get("package", "").lower())
        trivy_index[key] = f

    result = []
    for f in trivy_index.values():
        result.append(f)

    for f in osv:
        key = (f.get("vuln_id", "").upper(), f.get("package", "").lower())
        if key in trivy_index:
            # Trivy kaydı zaten var; sadece source güncelle
            trivy_index[key]["source"] = "both"
        else:
            result.append({**f, "source": "osv"})

    return result


def _severity_order(s: str) -> int:
    return {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(s.upper(), 4)


class SCAAgent(Agent):
    name = "sca"

    async def run(self, state: dict) -> AgentResult:
        repo_url = state["repo_url"]
        token = state.get("token", "")

        logger.info("[SCA] Başlıyor")

        repo_dir = state.get("temp_dir")
        base_dir = None
        if not repo_dir:
            logger.info("[SCA] temp_dir yok, repo indiriliyor")
            repo_dir, base_dir = await asyncio.to_thread(download_repo, repo_url, token)

        try:
            # 1. OSV.dev (lokal dosyalardan, GitHub API çağrısı yok)
            logger.info("[SCA] OSV.dev taraması başlıyor")
            osv_result = await asyncio.to_thread(
                analyze_dependencies_from_dir, repo_dir
            )
            osv_findings = osv_result.get("findings", [])
            packages_checked = osv_result.get("packages_checked", 0)
            logger.info("[SCA] OSV.dev: %d bulgu", len(osv_findings))

            # 2. Trivy (Docker — müsaitse)
            trivy_findings: list[dict] = []
            if is_docker_available():
                logger.info("[SCA] Trivy taraması başlıyor (Docker)")
                trivy_findings = await asyncio.to_thread(run_trivy, repo_dir)
                logger.info("[SCA] Trivy: %d bulgu", len(trivy_findings))
            else:
                logger.warning("[SCA] Docker mevcut değil, Trivy atlandı")

            # 3. Dedupe, CWE/OWASP zenginleştir
            all_findings = [enrich_finding(f) for f in _dedupe(osv_findings, trivy_findings)]
            all_findings.sort(key=lambda f: _severity_order(f.get("severity", "LOW")))

            severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for f in all_findings:
                sev = f.get("severity", "LOW").upper()
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            logger.info(
                "[SCA] Tamamlandı: %d toplam bulgu (C:%d H:%d M:%d L:%d)",
                len(all_findings),
                severity_counts["CRITICAL"],
                severity_counts["HIGH"],
                severity_counts["MEDIUM"],
                severity_counts["LOW"],
            )

            return AgentResult(
                agent_name=self.name,
                success=True,
                data={
                    "packages_checked": packages_checked,
                    "osv_count": len(osv_findings),
                    "trivy_count": len(trivy_findings),
                    "total_count": len(all_findings),
                    "severity_counts": severity_counts,
                    "docker_available": is_docker_available(),
                    "skipped_reason": osv_result.get("skipped_reason"),
                },
                findings=all_findings,
            )

        finally:
            if base_dir:
                import shutil
                shutil.rmtree(base_dir, ignore_errors=True)
