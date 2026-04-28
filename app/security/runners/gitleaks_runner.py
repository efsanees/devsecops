"""
Gitleaks runner — Docker üzerinde secret/credential taraması yapar.

zricethezav/gitleaks:latest imajı --no-git modunda çalışır:
  - Git geçmişi olmayan ZIP'ten indirilmiş repolar için doğru mod
  - API key, token, parola, private key, connection string vb. arar
  - 150+ varsayılan kural (AWS, GCP, GitHub, Stripe, Slack, vb.)

Güvenlik notu:
  Secret değerleri ASLA loglanmaz veya tam olarak raporlanmaz.
  _redact() ile ilk 4 + "..." + son 4 karakter gösterilir.

Çıktı dosyası:
  Gitleaks JSON'u stdout'a değil dosyaya yazar. Raporu /src altına
  yazıyoruz, host'tan okuyup temizliyoruz.
"""

import json
import logging
import os
import subprocess

from app.security.runners import _to_docker_path

logger = logging.getLogger(__name__)

GITLEAKS_IMAGE = "zricethezav/gitleaks:latest"
REPORT_FILENAME = ".gitleaks-report.json"


def _redact(secret: str) -> str:
    """
    Secret değerini kısmen maskeler: ilk 4 + '...' + son 4 karakter.
    Örnek: 'AKIAIOSFODNN7EXAMPLE' → 'AKIA...MPLE'
    8 karakterden kısa ise tamamen maskeler.
    """
    if not secret or len(secret) < 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"


def run_gitleaks(repo_dir: str, timeout: int = 120) -> list[dict]:
    """
    Gitleaks'i Docker'da çalıştırır, normalize edilmiş finding listesi döner.

    Args:
        repo_dir: Taranacak repo'nun host üzerindeki mutlak yolu.
        timeout:  Saniye cinsinden maksimum süre.

    Returns:
        [{"rule_id", "secret_type", "file", "line",
          "redacted_match", "severity", "entropy"}, ...]
    """
    docker_src = _to_docker_path(repo_dir)
    report_in_container = f"/src/{REPORT_FILENAME}"
    report_on_host = os.path.join(repo_dir, REPORT_FILENAME)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{docker_src}:/src",
        GITLEAKS_IMAGE,
        "detect",
        "--source", "/src",
        "--no-git",
        "--report-format", "json",
        "--report-path", report_in_container,
        "--redact",        # Gitleaks'in kendi redaction'ı da aktif
        "--no-banner",
    ]

    logger.info("[Gitleaks] Başlıyor")

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        logger.error("[Gitleaks] Zaman aşımı (%ds)", timeout)
        return []
    except FileNotFoundError:
        logger.error("[Gitleaks] Docker bulunamadı")
        return []

    # Exit 0 = temiz, Exit 1 = finding bulundu (ikisi de normal)
    # Exit 126+ = gerçek hata
    if proc.returncode > 1:
        logger.error("[Gitleaks] Hata (exit %d): %s", proc.returncode, proc.stderr[:300])
        return []

    # Rapor dosyasını oku
    if not os.path.exists(report_on_host):
        if proc.returncode == 0:
            logger.info("[Gitleaks] Temiz — bulgu yok")
            return []
        logger.warning("[Gitleaks] Rapor dosyası oluşturulmadı")
        return []

    try:
        with open(report_on_host, encoding="utf-8") as fh:
            raw_findings = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("[Gitleaks] Rapor okunamadı: %s", exc)
        raw_findings = []
    finally:
        # Rapor dosyasını hemen sil — secret değerleri disk üzerinde kalmasın
        try:
            os.unlink(report_on_host)
        except OSError:
            pass

    if not raw_findings:
        logger.info("[Gitleaks] Temiz — bulgu yok")
        return []

    findings = [_normalize(f) for f in (raw_findings or [])]
    logger.info("[Gitleaks] %d bulgu", len(findings))
    return findings


def _normalize(raw: dict) -> dict:
    """
    Gitleaks JSON bulgusunu ortak finding şemasına dönüştürür.
    Secret değeri ASLA tam olarak kaydedilmez.
    """
    secret_val = raw.get("Secret", "") or raw.get("Match", "")
    # Gitleaks --redact ile zaten kısmi maskeliyor olabilir,
    # biz de ek güvence olarak yeniden maskeliyoruz.
    redacted = _redact(secret_val)

    # Entropy yüksekliği gerçek secret olasılığını gösterir (>3 = yüksek)
    entropy = raw.get("Entropy", 0.0)
    severity = "HIGH" if entropy >= 3.0 else "MEDIUM"

    return {
        "source": "gitleaks",
        "type": "SECRET",
        "rule_id": raw.get("RuleID", ""),
        "secret_type": raw.get("Description", raw.get("RuleID", "Unknown")),
        "severity": severity,
        "file": raw.get("File", ""),
        "line": raw.get("StartLine"),
        "redacted_match": redacted,
        "entropy": round(entropy, 2),
        "tags": raw.get("Tags", []),
    }
