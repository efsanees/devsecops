import logging

logger = logging.getLogger(__name__)


def calculate_score(analysis: dict, yaml_text: str) -> dict:
    score = 0
    issues = []
    checks = {}

    # Test var mı? (15 puan)
    if analysis.get("has_tests"):
        score += 15
        checks["tests"] = True
    else:
        issues.append("Repo'da test dosyası bulunamadı")
        checks["tests"] = False

    # Docker var mı? (10 puan)
    if analysis.get("has_docker"):
        score += 10
        checks["docker"] = True
    else:
        issues.append("Dockerfile bulunamadı")
        checks["docker"] = False

    # Dil tespit edildi mi? (15 puan)
    if analysis.get("language") != "unknown":
        score += 15
        checks["language_detected"] = True
    else:
        issues.append("Programlama dili tespit edilemedi")
        checks["language_detected"] = False

    # Pipeline'da Trivy var mı? (25 puan)
    if "trivy" in yaml_text.lower():
        score += 25
        checks["trivy"] = True
    else:
        issues.append("Pipeline'da Trivy güvenlik taraması yok")
        checks["trivy"] = False

    # Pipeline'da test adımı var mı? (10 puan)
    if "test" in yaml_text.lower():
        score += 10
        checks["pipeline_tests"] = True
    else:
        issues.append("Pipeline'da test adımı bulunamadı")
        checks["pipeline_tests"] = False

    # Framework tespit edildi mi? (5 puan)
    if analysis.get("framework") != "unknown":
        score += 5
        checks["framework_detected"] = True
    else:
        issues.append("Framework tespit edilemedi")
        checks["framework_detected"] = False

    # Pipeline'da build adımı var mı? (10 puan)
    if "build" in yaml_text.lower():
        score += 10
        checks["pipeline_build"] = True
    else:
        issues.append("Pipeline'da build adımı bulunamadı")
        checks["pipeline_build"] = False

    # Checkout adımı var mı? (10 puan)
    if "actions/checkout" in yaml_text:
        score += 10
        checks["checkout"] = True
    else:
        issues.append("Pipeline'da checkout adımı bulunamadı")
        checks["checkout"] = False

    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"

    logger.info(f"Skor: {score}/100 ({grade})")

    return {
        "score": score,
        "max_score": 100,
        "grade": grade,
        "checks": checks,
        "issues": issues
    }
