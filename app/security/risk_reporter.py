"""
Risk Reporter
-------------
SAST + SCA bulgularını birleştirerek yapılandırılmış bir risk raporu üretir.

Risk skoru 100 üzerinden başlar; her bulgunun şiddetine göre puan düşülür.
OWASP Top 10 (2021) kategorileri Bandit kural kimliklerine göre eşlenir.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Severity → sıralama (düşük = daha kritik)
_SEVERITY_ORDER: dict[str, int] = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}

# Her bulgu için puan düşümü
_SEVERITY_DEDUCTION: dict[str, int] = {
    "CRITICAL": 30,
    "HIGH": 15,
    "MEDIUM": 7,
    "LOW": 2,
}

# Bandit kural ID → OWASP Top 10 (2021) kategorisi
_OWASP_MAP: dict[str, str] = {
    # Broken Access Control
    "B102": "A01:2021 – Broken Access Control",
    "B201": "A01:2021 – Broken Access Control",
    # Cryptographic Failures
    "B303": "A02:2021 – Cryptographic Failures",
    "B304": "A02:2021 – Cryptographic Failures",
    "B305": "A02:2021 – Cryptographic Failures",
    "B311": "A02:2021 – Cryptographic Failures",
    "B324": "A02:2021 – Cryptographic Failures",
    "B501": "A02:2021 – Cryptographic Failures",
    "B502": "A02:2021 – Cryptographic Failures",
    "B503": "A02:2021 – Cryptographic Failures",
    "B504": "A02:2021 – Cryptographic Failures",
    "B505": "A02:2021 – Cryptographic Failures",
    # Injection
    "B307": "A03:2021 – Injection",
    "B314": "A03:2021 – Injection",
    "B315": "A03:2021 – Injection",
    "B316": "A03:2021 – Injection",
    "B317": "A03:2021 – Injection",
    "B318": "A03:2021 – Injection",
    "B319": "A03:2021 – Injection",
    "B320": "A03:2021 – Injection",
    "B601": "A03:2021 – Injection",
    "B602": "A03:2021 – Injection",
    "B603": "A03:2021 – Injection",
    "B604": "A03:2021 – Injection",
    "B605": "A03:2021 – Injection",
    "B606": "A03:2021 – Injection",
    "B607": "A03:2021 – Injection",
    "B608": "A03:2021 – Injection",
    "B703": "A03:2021 – Injection",
    # Security Misconfiguration
    "B101": "A05:2021 – Security Misconfiguration",
    "B108": "A05:2021 – Security Misconfiguration",
    "B506": "A05:2021 – Security Misconfiguration",
    # Identification and Authentication Failures
    "B105": "A07:2021 – Identification and Authentication Failures",
    "B106": "A07:2021 – Identification and Authentication Failures",
    "B107": "A07:2021 – Identification and Authentication Failures",
    # Software and Data Integrity Failures
    "B301": "A08:2021 – Software and Data Integrity Failures",
    "B302": "A08:2021 – Software and Data Integrity Failures",
    "B403": "A08:2021 – Software and Data Integrity Failures",
    "B404": "A08:2021 – Software and Data Integrity Failures",
}

_DEFAULT_OWASP = "A09:2021 – Security Logging and Monitoring Failures"


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _risk_level(score: int) -> str:
    if score >= 80:
        return "LOW"
    if score >= 60:
        return "MEDIUM"
    if score >= 40:
        return "HIGH"
    return "CRITICAL"


def _enrich_finding(finding: dict) -> dict:
    """SAST bulgularına OWASP kategorisi ekler, diğerlerine dokunmaz."""
    if finding.get("type") == "SAST":
        issue_id = finding.get("issue_id", "")
        finding["owasp"] = _OWASP_MAP.get(issue_id, _DEFAULT_OWASP)
    return finding


# ---------------------------------------------------------------------------
# Dışa açık ana fonksiyon
# ---------------------------------------------------------------------------

def generate_risk_report(sast_result: dict, sca_result: dict) -> dict:
    """
    SAST ve SCA çıktılarını alıp kapsamlı bir risk raporu üretir.

    Döndürür::

        {
            "risk_score": int,          # 0-100
            "risk_level": str,          # LOW / MEDIUM / HIGH / CRITICAL
            "total_findings": int,
            "by_severity": {CRITICAL: n, HIGH: n, MEDIUM: n, LOW: n},
            "sast": { files_scanned, findings_count, skipped_reason },
            "sca":  { packages_checked, findings_count, skipped_reason },
            "top_findings": [...],      # ilk 10, severity'ye göre sıralı
            "all_findings": [...],
        }
    """
    sast_findings: list[dict] = sast_result.get("findings", [])
    sca_findings: list[dict] = sca_result.get("findings", [])
    all_findings = [_enrich_finding(f) for f in sast_findings + sca_findings]

    # Severity sayıları
    counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in all_findings:
        sev = f.get("severity", "LOW")
        counts[sev] = counts.get(sev, 0) + 1

    # Risk skoru
    deductions = sum(
        _SEVERITY_DEDUCTION.get(f.get("severity", "LOW"), 2)
        for f in all_findings
    )
    risk_score = max(0, 100 - deductions)

    # Severity'ye göre sırala
    sorted_findings = sorted(
        all_findings,
        key=lambda x: _SEVERITY_ORDER.get(x.get("severity", "LOW"), 3),
    )

    report = {
        "risk_score": risk_score,
        "risk_level": _risk_level(risk_score),
        "total_findings": len(all_findings),
        "by_severity": counts,
        "sast": {
            "files_scanned": sast_result.get("files_scanned", 0),
            "findings_count": len(sast_findings),
            "skipped_reason": sast_result.get("skipped_reason"),
        },
        "sca": {
            "packages_checked": sca_result.get("packages_checked", 0),
            "findings_count": len(sca_findings),
            "skipped_reason": sca_result.get("skipped_reason"),
        },
        "top_findings": sorted_findings[:10],
        "all_findings": sorted_findings,
    }

    logger.info(
        f"Risk raporu: {report['risk_level']} "
        f"({risk_score}/100) — {len(all_findings)} bulgu "
        f"[C:{counts['CRITICAL']} H:{counts['HIGH']} "
        f"M:{counts['MEDIUM']} L:{counts['LOW']}]"
    )
    return report
