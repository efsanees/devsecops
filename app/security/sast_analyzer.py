"""
SAST Analyzer — Bandit subprocess wrapper.

Tek public fonksiyon: run_bandit_on_dir(repo_dir)
SASTAgent tarafından çağrılır.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)

BANDIT_TIMEOUT = 90


def _bandit_executable() -> str:
    """Çalışan Python interpreter ile aynı dizindeki bandit binary'sini bulur."""
    scripts_dir = os.path.dirname(sys.executable)
    for name in ("bandit.exe", "bandit"):
        candidate = os.path.join(scripts_dir, name)
        if os.path.exists(candidate):
            return candidate
    return "bandit"  # PATH'e güven


def _run_bandit(tmp_dir: str) -> tuple[list[dict], str | None]:
    """Bandit çalıştırır. (findings, hata_nedeni) döndürür."""
    try:
        proc = subprocess.run(
            [_bandit_executable(), "-r", tmp_dir, "-f", "json", "-q", "--exit-zero"],
            capture_output=True, text=True, timeout=BANDIT_TIMEOUT,
        )
    except FileNotFoundError:
        return [], "Bandit kurulu değil (`pip install bandit`)"
    except subprocess.TimeoutExpired:
        return [], "Bandit zaman aşımına uğradı"

    raw = proc.stdout.strip() or proc.stderr.strip()
    if not raw:
        return [], None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"Bandit JSON parse hatası: {exc}")
        return [], "Bandit çıktısı ayrıştırılamadı"

    findings: list[dict] = []
    for issue in data.get("results", []):
        fname = issue.get("filename", "")
        fname = fname.replace(tmp_dir + os.sep, "").replace(tmp_dir + "/", "")

        sev = issue.get("issue_severity", "MEDIUM").upper()
        if sev not in ("HIGH", "MEDIUM", "LOW"):
            sev = "MEDIUM"

        findings.append({
            "type": "SAST",
            "severity": sev,
            "confidence": issue.get("issue_confidence", "MEDIUM").upper(),
            "file": fname,
            "line": issue.get("line_number"),
            "issue_id": issue.get("test_id", ""),
            "rule_id": issue.get("test_id", ""),
            "issue_name": issue.get("test_name", ""),
            "summary": issue.get("issue_text", ""),
            "message": issue.get("issue_text", ""),
            "more_info": issue.get("more_info", ""),
            "code_snippet": issue.get("code", "").strip(),
        })

    return findings, None


def run_bandit_on_dir(repo_dir: str) -> list[dict]:
    """
    İndirilmiş repo dizini üzerinde Bandit çalıştırır.
    SASTAgent tarafından kullanılır.
    """
    findings, error = _run_bandit(repo_dir)
    if error:
        logger.warning("Bandit hatası: %s", error)
    for f in findings:
        f["source"] = "bandit"
    return findings
