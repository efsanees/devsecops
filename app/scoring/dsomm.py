"""
DSOMM (DevSecOps Maturity Model) tabanlı güvenlik olgunluk skoru.

5 kategori, toplam 100 puan:
  Build & Deployment   30 puan
  Testing              25 puan
  Implementation       25 puan
  Information Gathering 10 puan
  Culture & Org        10 puan

Seviyeler:
  Başlangıç : 0-39
  Gelişen   : 40-69
  Olgun     : 70-100
"""

from __future__ import annotations


def calculate_dsomm(
    profile: dict,
    pipeline_result: dict,
    sast_result: dict,
    sca_result: dict,
    secret_result: dict,
    file_list: list[str],
) -> dict:
    """
    Tüm agent sonuçlarından DSOMM skoru hesaplar.

    Args:
        profile:         ProjectProfilerAgent.data
        pipeline_result: PipelineAnalyzerAgent.data
        sast_result:     SASTAgent.data
        sca_result:      SCAAgent.data
        secret_result:   SecretAgent.data
        file_list:       Repo dosya listesi (kültür kontrolleri için)

    Returns:
        {
          total_score, level,
          categories: {
            build_deployment, testing, implementation,
            information_gathering, culture_org
          },
          details: {...}  ← her kontrol açıklaması
        }
    """
    categories: dict[str, int] = {}
    details: dict[str, dict] = {}

    # ── 1. Build & Deployment (30 puan) ──────────────────────────────────
    bd_score = 0
    bd_checks: dict[str, bool] = {}

    has_pipeline = pipeline_result.get("has_pipeline", False)
    detected_steps = set()
    for p in pipeline_result.get("existing_pipelines", []):
        detected_steps.update(p.get("detected_steps", []))

    bd_checks["pipeline_exists"] = has_pipeline
    if has_pipeline:
        bd_score += 10

    bd_checks["docker_present"] = profile.get("has_docker", False)
    if profile.get("has_docker"):
        bd_score += 10

    bd_checks["build_step"] = "build" in detected_steps
    if "build" in detected_steps:
        bd_score += 5

    bd_checks["deploy_step"] = "deploy" in detected_steps
    if "deploy" in detected_steps:
        bd_score += 5

    categories["build_deployment"] = bd_score
    details["build_deployment"] = bd_checks

    # ── 2. Testing (25 puan) ─────────────────────────────────────────────
    t_score = 0
    t_checks: dict[str, bool] = {}

    t_checks["has_test_files"] = profile.get("has_tests", False)
    if profile.get("has_tests"):
        t_score += 10

    t_checks["sast_in_pipeline"] = "sast" in detected_steps
    if "sast" in detected_steps:
        t_score += 5

    t_checks["sca_in_pipeline"] = "sca" in detected_steps
    if "sca" in detected_steps:
        t_score += 5

    t_checks["secret_scan_in_pipeline"] = "secret_scan" in detected_steps
    if "secret_scan" in detected_steps:
        t_score += 5

    categories["testing"] = t_score
    details["testing"] = t_checks

    # ── 3. Implementation (25 puan) ───────────────────────────────────────
    # Güvenlik açığı sayısına göre düşen puan sistemi.
    # Docker yoksa Semgrep/Trivy atlandı → tarama eksik → max puan düşürülür.
    impl_score = 0

    docker_available = sast_result.get("docker_available", True)

    sast_sev = sast_result.get("severity_counts", {})
    sast_critical = sast_sev.get("HIGH", 0) + sast_sev.get("CRITICAL", 0)
    # Docker varsa max 15, yoksa Semgrep atlandığı için max 8
    sast_max = 15 if docker_available else 8
    sast_pts = max(0, sast_max - sast_critical * 2)
    impl_score += sast_pts

    sca_sev = sca_result.get("severity_counts", {})
    sca_critical = sca_sev.get("CRITICAL", 0) + sca_sev.get("HIGH", 0)
    # Docker varsa max 10, yoksa Trivy atlandığı için max 6
    sca_max = 10 if docker_available else 6
    sca_pts = max(0, sca_max - sca_critical * 2)
    impl_score += sca_pts

    categories["implementation"] = impl_score
    details["implementation"] = {
        "sast_high_count": sast_critical,
        "sast_points": sast_pts,
        "sca_critical_high_count": sca_critical,
        "sca_points": sca_pts,
        "docker_available": docker_available,
        "note": None if docker_available else "Semgrep/Trivy atlandı — tam tarama için Docker gerekli",
    }

    # ── 4. Information Gathering (10 puan) ────────────────────────────────
    # Docker yoksa Gitleaks atlandı → "0 secret" doğru olmayabilir, max'ı düşür.
    secret_count = secret_result.get("total_count", 0)
    secret_skipped = bool(secret_result.get("skipped_reason"))
    ig_max = 5 if secret_skipped else 10
    if secret_count == 0:
        ig_score = ig_max
    else:
        ig_score = max(0, ig_max - secret_count * 2)
    categories["information_gathering"] = ig_score
    details["information_gathering"] = {
        "hardcoded_secrets_found": secret_count,
        "scanner_skipped": secret_skipped,
        "max_points": ig_max,
        "points": ig_score,
    }

    # ── 5. Culture & Org (10 puan) ────────────────────────────────────────
    file_names_lower = {f.lower() for f in file_list}
    has_readme = any("readme" in f for f in file_names_lower)
    has_security = any("security.md" in f for f in file_names_lower)
    has_contributing = any("contributing" in f for f in file_names_lower)

    co_score = 0
    if has_readme:
        co_score += 4
    if has_security:
        co_score += 3
    if has_contributing:
        co_score += 3

    categories["culture_org"] = co_score
    details["culture_org"] = {
        "has_readme": has_readme,
        "has_security_md": has_security,
        "has_contributing": has_contributing,
    }

    # ── Toplam ────────────────────────────────────────────────────────────
    total = sum(categories.values())
    level = (
        "Olgun" if total >= 70
        else "Gelişen" if total >= 40
        else "Başlangıç"
    )

    return {
        "total_score": total,
        "max_score": 100,
        "level": level,
        "categories": categories,
        "details": details,
    }
