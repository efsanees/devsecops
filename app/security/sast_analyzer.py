"""
SAST (Static Application Security Testing) Analyzer
-----------------------------------------------------
GitHub API'den Python kaynak dosyalarını geçici bir dizine indirir ve
Bandit'i subprocess üzerinden çalıştırır.

Dil kısıtı YOK: all_files listesinde .py dosyası varsa her zaman taranır.
Bandit kurulu değilse veya dosya bulunamazsa skipped_reason ile açıklanır.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from typing import Callable

logger = logging.getLogger(__name__)

MAX_FILES = 60
BANDIT_TIMEOUT = 90

_EXCLUDED_DIRS = ("venv/", ".venv/", "migrations/", "node_modules/", ".git/", "dist/", "build/", "__pycache__/")
_EXCLUDED_NAMES = ("conftest.py",)  # manage.py KASITLI olarak dahil — Django güvenlik bulguları önemli


def _collect_python_files(all_files: list[str]) -> list[str]:
    selected: list[str] = []
    for f in all_files:
        if not f.endswith(".py"):
            continue
        if any(f.startswith(ex) or f"/{ex.rstrip('/')}" in f for ex in _EXCLUDED_DIRS):
            continue
        if os.path.basename(f) in _EXCLUDED_NAMES:
            continue
        selected.append(f)

    src = [f for f in selected if "test" not in f.lower()]
    tests = [f for f in selected if "test" in f.lower()]
    return (src + tests)[:MAX_FILES]


def _run_bandit(tmp_dir: str) -> tuple[list[dict], str | None]:
    """Bandit çalıştırır. (findings, hata_nedeni) döndürür."""
    try:
        proc = subprocess.run(
            ["bandit", "-r", tmp_dir, "-f", "json", "-q", "--exit-zero"],
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
            "issue_name": issue.get("test_name", ""),
            "summary": issue.get("issue_text", ""),
            "more_info": issue.get("more_info", ""),
            "code_snippet": issue.get("code", "").strip(),
        })

    return findings, None


def analyze_static(
    repo_url: str,
    token: str,
    all_files: list[str],
    language: str,
    get_file_content_fn: Callable,
) -> dict:
    """
    Tüm .py dosyalarını tarar — dil parametresine bakılmaksızın.

    Döndürür:
        { files_scanned, findings, skipped_reason (opsiyonel) }
    """
    py_files = _collect_python_files(all_files)

    if not py_files:
        if not all_files:
            reason = "Repo dosya listesi alınamadı — GitHub token ekleyip tekrar deneyin"
        elif language not in ("Python", "unknown"):
            reason = f"{language} için SAST henüz desteklenmiyor (yakında: Java, Go)"
        else:
            reason = "Repo'da Python dosyası bulunamadı"
        logger.info(f"SAST atlandı: {reason}")
        return {"files_scanned": 0, "findings": [], "skipped_reason": reason}

    logger.info(f"SAST: {len(py_files)} Python dosyası indiriliyor")

    with tempfile.TemporaryDirectory(prefix="sast_") as tmp_dir:
        fetched = 0
        for path in py_files:
            content = get_file_content_fn(repo_url, token, path)
            if content is None:
                continue
            dest = os.path.join(tmp_dir, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                with open(dest, "w", encoding="utf-8") as fh:
                    fh.write(content)
                fetched += 1
            except OSError as exc:
                logger.warning(f"Dosya yazılamadı ({path}): {exc}")

        if fetched == 0:
            return {
                "files_scanned": 0,
                "findings": [],
                "skipped_reason": "Dosya içerikleri indirilemedi — token gerekebilir",
            }

        logger.info(f"SAST: Bandit {fetched} dosyaya çalıştırılıyor")
        findings, error = _run_bandit(tmp_dir)

    result: dict = {"files_scanned": fetched, "findings": findings}
    if error:
        result["skipped_reason"] = error
    logger.info(f"SAST tamamlandı: {fetched} dosya, {len(findings)} bulgu")
    return result


def run_bandit_on_dir(repo_dir: str) -> list[dict]:
    """
    İndirilmiş repo dizini üzerinde Bandit çalıştırır.
    SASTAgent tarafından kullanılır (dosya bazlı indirme yerine tam dizin).
    """
    findings, error = _run_bandit(repo_dir)
    if error:
        logger.warning("Bandit hatası: %s", error)
    # source alanı ekle — SASTAgent normalizasyonu için
    for f in findings:
        f["source"] = "bandit"
    return findings
