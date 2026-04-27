"""
Compliance Scoring — 8 kriter, 100 puan, platform-aware
"""

import logging

logger = logging.getLogger(__name__)


def calculate_score(analysis: dict, yaml_text: str, platform: str = "github_actions") -> dict:
    score = 0
    issues = []
    checks = {}

    # Test var mi? (15 puan)
    if analysis.get("has_tests"):
        score += 15
        checks["tests"] = True
    else:
        issues.append("Repo'da test dosyasi bulunamadi")
        checks["tests"] = False

    # Docker var mi? (10 puan)
    if analysis.get("has_docker"):
        score += 10
        checks["docker"] = True
    else:
        issues.append("Dockerfile bulunamadi")
        checks["docker"] = False

    # Dil tespit edildi mi? (15 puan)
    if analysis.get("language") != "unknown":
        score += 15
        checks["language_detected"] = True
    else:
        issues.append("Programlama dili tespit edilemedi")
        checks["language_detected"] = False

    # Pipeline'da Trivy/guvenlik taramasi var mi? (25 puan)
    has_trivy = "trivy" in yaml_text.lower() or "aquasec" in yaml_text.lower() or "gitleaks" in yaml_text.lower()
    if has_trivy:
        score += 25
        checks["security_scan"] = True
    else:
        issues.append("Pipeline'da guvenlik taramasi yok (Trivy oneriliyor)")
        checks["security_scan"] = False

    # Pipeline'da test adimi var mi? (10 puan)
    if "test" in yaml_text.lower():
        score += 10
        checks["pipeline_tests"] = True
    else:
        issues.append("Pipeline'da test adimi bulunamadi")
        checks["pipeline_tests"] = False

    # Framework tespit edildi mi? (5 puan)
    if analysis.get("framework") != "unknown":
        score += 5
        checks["framework_detected"] = True
    else:
        issues.append("Framework tespit edilemedi")
        checks["framework_detected"] = False

    # Pipeline'da build adimi var mi? (10 puan)
    if "build" in yaml_text.lower() or "install" in yaml_text.lower() or "compile" in yaml_text.lower():
        score += 10
        checks["pipeline_build"] = True
    else:
        issues.append("Pipeline'da build/install adimi bulunamadi")
        checks["pipeline_build"] = False

    # Checkout / kaynak kod alimi var mi? (10 puan) — platform'a gore
    checkout_ok = False
    if platform == "github_actions":
        checkout_ok = "actions/checkout" in yaml_text
    elif platform == "gitlab_ci":
        checkout_ok = "stages:" in yaml_text  # GitLab otomatik checkout yapar
    elif platform == "jenkins":
        checkout_ok = "checkout scm" in yaml_text or "checkout(" in yaml_text

    if checkout_ok:
        score += 10
        checks["checkout"] = True
    else:
        issues.append("Pipeline'da kaynak kod alma adimi bulunamadi")
        checks["checkout"] = False

    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"
    logger.info(f"Skor: {score}/100 ({grade}) [{platform}]")

    return {
        "score": score,
        "max_score": 100,
        "grade": grade,
        "platform": platform,
        "checks": checks,
        "issues": issues,
    }
