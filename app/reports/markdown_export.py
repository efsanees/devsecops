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

    return {
        "repo_url":          job_result.get("repo_url", "—"),
        "repo_name":         job_result.get("repo_url", "").replace("https://github.com/", ""),
        "analyzed_at":       analyzed_at,
        "platform":          job_result.get("platform", "github_actions"),
        "elapsed_seconds":   job_result.get("elapsed_seconds"),
        "profile":           job_result.get("profile", {}),
        "dsomm":             job_result.get("dsomm", {}),
        "pipeline_analysis": pipeline_analysis,
        "sast_findings":     findings.get("sast", []),
        "sca_findings":      findings.get("sca", []),
        "secret_findings":   findings.get("secret", []),
        "pipeline_findings": findings.get("pipeline", []),
        "llm_summary":       job_result.get("llm_summary", ""),
        "pipeline_yaml":     job_result.get("pipeline_yaml", ""),
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
