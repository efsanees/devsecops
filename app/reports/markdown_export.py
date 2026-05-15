"""
Markdown rapor üretici — Jinja2 şablonundan render eder.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _build_context(job_result: dict) -> dict:
    findings = job_result.get("findings", {})
    pipeline_analysis = job_result.get("pipeline_analysis", {})
    analyzed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sast = findings.get("sast", [])
    sca  = findings.get("sca", [])
    secret = findings.get("secret", [])
    pipeline_findings = findings.get("pipeline", [])

    # Tüm bulgular — OWASP dağılımı için
    all_findings = [*sast, *sca, *secret]
    owasp_dist: dict[str, int] = {}
    for f in all_findings:
        cat = f.get("owasp_category")
        if cat:
            owasp_dist[cat] = owasp_dist.get(cat, 0) + 1

    # Severity sırasına göre top 5 kritik bulgu
    _sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    top_critical = sorted(
        all_findings,
        key=lambda f: _sev_order.get(f.get("severity", "LOW"), 4),
    )[:5]

    return {
        "repo_url":           job_result.get("repo_url", "—"),
        "repo_name":          job_result.get("repo_url", "").replace("https://github.com/", ""),
        "analyzed_at":        analyzed_at,
        "platform":           job_result.get("platform", "github_actions"),
        "elapsed_seconds":    job_result.get("elapsed_seconds"),
        "profile":            job_result.get("profile", {}),
        "dsomm":              job_result.get("dsomm", {}),
        "pipeline_analysis":  pipeline_analysis,
        "sast_findings":      sast,
        "sca_findings":       sca,
        "secret_findings":    secret,
        "pipeline_findings":  pipeline_findings,
        "llm_summary":        job_result.get("llm_summary", ""),
        "pipeline_yaml":      job_result.get("pipeline_yaml", ""),
        # Akademik rapor için ek alanlar
        "owasp_distribution": owasp_dist,
        "top_critical_findings": top_critical,
        "tool_versions": {
            "Bandit":  "1.7.x",
            "Semgrep": "1.x (Docker)",
            "Trivy":   "0.x (Docker)",
            "OSV.dev": "API v1",
            "Gitleaks": "8.x (Docker)",
        },
    }


def render_markdown(job_result: dict) -> str:
    """
    Job sonucundan Markdown rapor üretir.

    Args:
        job_result: Orchestrator'ın döndürdüğü / DB'deki result dict.

    Returns:
        Markdown string.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("report.md.j2")
    ctx = _build_context(job_result)
    return template.render(**ctx)
