"""
Trivy runner — Docker üzerinde filesystem taraması yapar.

aquasec/trivy:latest imajı --scanners vuln ile:
  - requirements.txt, package.json, pom.xml, go.mod, Cargo.lock
  - *.csproj, Gemfile.lock, composer.lock
  - ikili dosyalar (SBOM benzeri analiz)

DB cache: ~/.cache/trivy host'a mount edilir — her çalıştırmada yeniden
indirmek gerekmez (~200 MB, ~2-3 dakika ilk indirme).
"""

import logging
import os
import platform

from app.security.runners import run_docker_tool

logger = logging.getLogger(__name__)

TRIVY_IMAGE = "aquasec/trivy:latest"


def _trivy_cache_dir() -> str:
    """Platform bağımsız Trivy cache dizini."""
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~/.cache")
    cache = os.path.join(base, "trivy")
    os.makedirs(cache, exist_ok=True)
    return cache


def _to_docker_cache_path(host_path: str) -> str:
    """Cache dizini için de Windows → Docker path dönüşümü."""
    from app.security.runners import _to_docker_path
    return _to_docker_path(host_path)


def run_trivy(repo_dir: str, timeout: int = 360) -> list[dict]:
    """
    Trivy'yi Docker'da dosya sistemi taraması modunda çalıştırır.

    Args:
        repo_dir: Taranacak repo'nun host üzerindeki mutlak yolu.
        timeout:  Saniye (ilk çalıştırmada DB indirme dahil ~5 dk).

    Returns:
        [{"vuln_id", "package", "version", "severity",
          "fixed_in", "summary", "source", "ecosystem"}, ...]
    """
    cache_dir = _trivy_cache_dir()
    docker_cache = _to_docker_cache_path(cache_dir)

    from app.security.runners import _to_docker_path
    docker_repo = _to_docker_path(repo_dir)

    # Trivy için manuel komut kuruyoruz: iki volume mount gerekiyor
    import subprocess, json as _json

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{docker_repo}:/src",
        "-v", f"{docker_cache}:/root/.cache/trivy",
        TRIVY_IMAGE,
        "fs",
        "--scanners", "vuln",
        "--format", "json",
        "--severity", "CRITICAL,HIGH,MEDIUM",
        "--quiet",
        "/src",
    ]

    logger.info("[Trivy] Komut: %s", " ".join(cmd))

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        logger.error("[Trivy] Zaman aşımı (%ds)", timeout)
        return []
    except FileNotFoundError:
        logger.error("[Trivy] Docker bulunamadı")
        return []

    # Trivy exit 0 = temiz, exit 1 = bulgu var (her ikisi de normal)
    stdout = proc.stdout.strip()
    if not stdout:
        logger.warning("[Trivy] stdout boş")
        return []

    try:
        raw = _json.loads(stdout)
    except _json.JSONDecodeError as exc:
        logger.error("[Trivy] JSON parse hatası: %s", exc)
        return []

    findings = []
    for result in raw.get("Results", []):
        for vuln in result.get("Vulnerabilities") or []:
            findings.append(_normalize(vuln, result))

    logger.info("[Trivy] %d bulgu", len(findings))
    return findings


def _normalize(vuln: dict, result: dict) -> dict:
    """Trivy JSON bulgusunu ortak SCA finding şemasına dönüştürür."""
    cvss_score = None
    for source in vuln.get("CVSS", {}).values():
        score = source.get("V3Score") or source.get("V2Score")
        if score:
            try:
                cvss_score = float(score)
            except (TypeError, ValueError):
                pass
            break

    # Trivy'nin severity değerleri zaten CRITICAL/HIGH/MEDIUM/LOW
    severity = vuln.get("Severity", "MEDIUM").upper()

    return {
        "source": "trivy",
        "type": "SCA",
        "vuln_id": vuln.get("VulnerabilityID", ""),
        "package": vuln.get("PkgName", ""),
        "version": vuln.get("InstalledVersion", ""),
        "fixed_in": vuln.get("FixedVersion", "bilinmiyor") or "bilinmiyor",
        "severity": severity,
        "cvss_score": cvss_score,
        "summary": vuln.get("Title") or vuln.get("Description", "")[:200],
        "ecosystem": result.get("Type", ""),
        "aliases": [],
    }
