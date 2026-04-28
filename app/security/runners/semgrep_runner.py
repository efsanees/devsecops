"""
Semgrep runner — Docker üzerinde çalıştırır.

semgrep/semgrep:latest imajı --config=auto ile dili otomatik algılar:
Python → bandit kuralları + p/python, JS/TS → p/javascript, Go → p/golang vb.

Çıktı JSON formatında stdout'a yazılır, parse edilerek finding listesi döner.
"""

import logging

from app.security.runners import run_docker_tool

logger = logging.getLogger(__name__)

SEMGREP_IMAGE = "semgrep/semgrep:latest"

# Semgrep exit code'ları:
#   0 = temiz
#   1 = finding bulundu (NORMAL — hata değil)
#   2 = gerçek hata
# run_docker_tool zaten 0 ve 1'i kabul ediyor.

# Taramadan hariç tutulacak klasörler (false positive azaltır, hız artar)
EXCLUDE_PATTERNS = [
    "--exclude-rule", "generic.secrets",   # gitleaks yapacak bunu
    "--exclude", "node_modules",
    "--exclude", ".venv",
    "--exclude", "venv",
    "--exclude", "dist",
    "--exclude", "build",
]


def run_semgrep(repo_dir: str, timeout: int = 300) -> list[dict]:
    """
    Semgrep'i Docker'da çalıştırır, normalize edilmiş finding listesi döner.

    Args:
        repo_dir: Taranacak repo'nun host üzerindeki mutlak yolu.
        timeout:  Saniye cinsinden maksimum süre (büyük repolar ~3-4 dk).

    Returns:
        [{"rule_id", "severity", "file", "line", "message", "owasp_category"}, ...]
    """
    extra_args = [
        "semgrep",
        "--config", "auto",
        "--json",
        "--quiet",          # stderr'e ilerleme yazmasın
        "--no-rewrite-rule-ids",
        *EXCLUDE_PATTERNS,
        "/src",
    ]

    try:
        raw = run_docker_tool(
            image=SEMGREP_IMAGE,
            repo_dir=repo_dir,
            extra_args=extra_args,
            timeout=timeout,
        )
    except Exception as exc:
        logger.error("Semgrep Docker hatası: %s", exc)
        return []

    results = raw.get("results", []) if isinstance(raw, dict) else []
    logger.info("Semgrep: %d ham bulgu", len(results))
    return [_normalize(r) for r in results]


def _normalize(raw: dict) -> dict:
    """Semgrep JSON sonucunu ortak finding şemasına dönüştürür."""
    extra = raw.get("extra", {})
    meta = extra.get("metadata", {})

    severity_raw = extra.get("severity", "WARNING").upper()
    severity_map = {"ERROR": "HIGH", "WARNING": "MEDIUM", "INFO": "LOW"}
    severity = severity_map.get(severity_raw, "MEDIUM")

    # Semgrep OWASP metadata'yı liste ya da string olarak verebilir
    owasp_raw = meta.get("owasp") or meta.get("owasp-id") or ""
    if isinstance(owasp_raw, list):
        owasp = owasp_raw[0] if owasp_raw else ""
    else:
        owasp = str(owasp_raw)

    return {
        "source": "semgrep",
        "type": "SAST",
        "rule_id": raw.get("check_id", ""),
        "severity": severity,
        "file": raw.get("path", "").lstrip("/src/"),
        "line": raw.get("start", {}).get("line"),
        "message": extra.get("message", ""),
        "owasp_category": owasp or None,
        "fix": extra.get("fix") or None,
    }
