"""
PR Review Service — GitHub PR'larına otomatik güvenlik analizi yorum ekler.

Akış:
  1. PR'da değişen dosyaları çek (GitHub API)
  2. Değişen .py dosyaları üzerine Bandit çalıştır
  3. Tüm değişen dosyalar üzerine Semgrep çalıştır (Docker varsa)
  4. LLM false positive filtresi uygula
  5. Baseline karşılaştırması: bu repo için son tamamlanmış job'daki
     aynı dosyaların bulgularıyla karşılaştır (yeni / düzeltilmiş)
  6. Markdown PR comment oluştur:
     - Özet (dosya, sorun, FP, baseline diff)
     - CWE + OWASP kategorileri
     - AI fix önerileri
  7. GitHub PR'a comment gönder

Gerekli env değişkenleri:
  GITHUB_TOKEN  — PR'a comment atmak için (repo:public_repo kapsamı yeterli)
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile

import requests

from app.scoring.cwe_owasp_mapper import enrich_finding
from app.security.sast_analyzer import run_bandit_on_dir
from app.security.runners import is_docker_available
from app.security.runners.semgrep_runner import run_semgrep
from app.services.fp_filter import filter_false_positives

logger = logging.getLogger(__name__)

# ── GitHub API yardımcıları ────────────────────────────────────────────────────

def _gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_changed_files(owner: str, repo: str, pr_number: int, token: str) -> list[dict]:
    """PR'da değişen dosyaların listesini döner."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    try:
        resp = requests.get(url, headers=_gh_headers(token), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("[PRReview] Dosya listesi alınamadı: %s", exc)
        return []


def _download_file(owner: str, repo: str, path: str, ref: str, token: str) -> str | None:
    """Belirtilen commit/branch'daki dosya içeriğini indir."""
    import base64
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    try:
        resp = requests.get(url, headers=_gh_headers(token),
                            params={"ref": ref}, timeout=10)
        if resp.status_code != 200:
            return None
        return base64.b64decode(resp.json()["content"]).decode("utf-8", errors="ignore")
    except Exception:
        return None


def _post_pr_comment(owner: str, repo: str, pr_number: int,
                     body: str, token: str) -> bool:
    """PR'a Markdown comment gönderir."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    try:
        resp = requests.post(url, headers=_gh_headers(token),
                             json={"body": body}, timeout=15)
        resp.raise_for_status()
        logger.info("[PRReview] Comment gönderildi: PR #%d", pr_number)
        return True
    except Exception as exc:
        logger.error("[PRReview] Comment gönderilemedi: %s", exc)
        return False


# ── Bulgu karşılaştırma (baseline) ───────────────────────────────────────────

def _finding_key(f: dict) -> str:
    """Bulguyu benzersiz tanımlayan anahtar (dosya + satır + kural)."""
    return f"{f.get('file','')}:{f.get('line','')}:{f.get('rule_id','')}"


def _compare_with_baseline(
    new_findings: list[dict],
    baseline_findings: list[dict],
    changed_files: set[str],
) -> tuple[list[dict], list[dict]]:
    """
    Returns: (added_findings, fixed_findings)
    - added:  PR'da yeni çıkan, baseline'da olmayan bulgular
    - fixed:  Baseline'da olan ama PR'da olmayan bulgular (değişen dosyalarda)
    """
    # Baseline'daki bulgular — sadece değişen dosyalar
    baseline_in_changed = [
        f for f in baseline_findings
        if any(f.get("file", "").endswith(cf) or cf.endswith(f.get("file", ""))
               for cf in changed_files)
    ]

    baseline_keys = {_finding_key(f) for f in baseline_in_changed}
    new_keys      = {_finding_key(f) for f in new_findings}

    added = [f for f in new_findings       if _finding_key(f) not in baseline_keys]
    fixed = [f for f in baseline_in_changed if _finding_key(f) not in new_keys]

    return added, fixed


def _get_baseline_findings(repo_url: str) -> list[dict]:
    """DB'den bu repo için en son tamamlanmış job'un SAST bulgularını döner."""
    try:
        from app.database import SessionLocal
        from app.models.job import Job
        from sqlalchemy import desc

        with SessionLocal() as db:
            job = (
                db.query(Job)
                .filter(Job.repo_url == repo_url, Job.status == "completed")
                .order_by(desc(Job.finished_at))
                .first()
            )
            if not job or not job.result:
                return []
            return (job.result.get("findings") or {}).get("sast") or []
    except Exception as exc:
        logger.warning("[PRReview] Baseline alınamadı: %s", exc)
        return []


# ── Markdown comment şablonu ──────────────────────────────────────────────────

_SEV_ICON = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}


def _format_finding(f: dict) -> str:
    icon    = _SEV_ICON.get(f.get("severity", ""), "⚪")
    sev     = f.get("severity", "")
    msg     = f.get("message") or f.get("summary") or f.get("rule_id") or "—"
    loc     = f"{f.get('file','')}:{f.get('line','')}" if f.get("file") else ""
    rule    = f.get("rule_id", "")
    cwe     = f.get("cwe_id", "")
    owasp   = f.get("owasp_category", "")
    fix     = f.get("fix_suggestion", "")

    parts = [f"{icon} **{sev}** — {msg}"]
    badges = []
    if loc:    badges.append(f"`{loc}`")
    if rule:   badges.append(f"Kural: `{rule}`")
    if cwe:    badges.append(f"`{cwe}`")
    if owasp:  badges.append(f"`{owasp}`")
    if badges: parts.append(" · ".join(badges))
    if fix:    parts.append(f"  > 💡 **Düzeltme:** {fix}")

    return "\n".join(parts)


def _build_comment(
    owner: str, repo: str, pr_number: int,
    all_findings: list[dict], fp_list: list[dict],
    added: list[dict], fixed: list[dict],
    files_scanned: int,
) -> str:
    total = len(all_findings)
    high  = sum(1 for f in all_findings if f.get("severity") in ("HIGH", "CRITICAL"))
    med   = sum(1 for f in all_findings if f.get("severity") == "MEDIUM")

    # Özet satırı
    lines = [
        "## 🔍 DevSecOps Code Review",
        "",
        f"{files_scanned} dosya tarandı · "
        f"**{total}** sorun bulundu "
        f"({high} kritik/yüksek · {med} orta)",
        "",
    ]

    # FP bilgisi
    if fp_list:
        lines += [
            "> [!NOTE]",
            f"> **LLM False Positive Analizi:** "
            f"{total + len(fp_list)} SAST bulgusundan "
            f"**{len(fp_list)}** tanesi false positive olarak filtrelendi "
            f"(güven eşiği: %65).",
            "",
        ]

    # Baseline karşılaştırması
    if added or fixed:
        lines.append("> [!IMPORTANT]")
        if added:
            lines.append(f"> 🆕 Bu PR **{len(added)} yeni** güvenlik sorunu getiriyor.")
        if fixed:
            lines.append(f"> ✅ Bu PR **{len(fixed)} sorunu** düzeltiyor.")
        lines.append("")

    if high:
        lines.append("> [!CAUTION]")
        lines.append(
            f"> Bu PR'da **{high} yüksek öncelikli güvenlik açığı** var. "
            "Merge etmeden önce düzeltilmesi önerilir."
        )
        lines.append("")

    # Dosya bazında bulgular — dosyaya göre grupla
    by_file: dict[str, list[dict]] = {}
    for f in all_findings:
        fname = f.get("file") or "bilinmeyen dosya"
        by_file.setdefault(fname, []).append(f)

    for fname, ffindings in sorted(by_file.items()):
        lines += [f"### 📄 `{fname}`", ""]
        for f in sorted(ffindings, key=lambda x: (
            {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(x.get("severity", ""), 4)
        )):
            lines.append(_format_finding(f))
            lines.append("")

    # Düzeltilen bulgular (varsa)
    if fixed:
        lines += ["<details>", "<summary>✅ Düzeltilen Sorunlar</summary>", ""]
        for f in fixed:
            lines.append(_format_finding(f))
            lines.append("")
        lines += ["</details>", ""]

    lines += [
        "---",
        "_Bu analiz [DevSecOps AI](https://github.com) tarafından otomatik olarak yapılmıştır._",
    ]

    return "\n".join(lines)


# ── Ana entry point ───────────────────────────────────────────────────────────

async def run_pr_review(
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
    repo_url: str,
    token: str,
    github_token: str,
) -> dict:
    """
    PR analizi yürütür ve comment gönderir.

    Args:
        owner/repo:    GitHub repo koordinatları
        pr_number:     Pull request numarası
        head_sha:      PR'ın HEAD commit SHA'sı
        repo_url:      Tam HTTPS repo URL'i
        token:         Kaynak kod okuma tokeni (opsiyonel)
        github_token:  Comment atmak için GitHub PAT

    Returns:
        {"files_scanned", "total_findings", "fp_filtered", "comment_posted"}
    """
    logger.info("[PRReview] Başlıyor: %s/%s PR#%d", owner, repo, pr_number)

    # 1. Değişen dosyalar
    changed_files_data = await asyncio.to_thread(
        _get_changed_files, owner, repo, pr_number, github_token
    )
    py_files  = [f["filename"] for f in changed_files_data if f["filename"].endswith(".py")]
    all_files = [f["filename"] for f in changed_files_data]
    changed_set = set(all_files)

    if not all_files:
        logger.info("[PRReview] Değişen dosya yok")
        return {"files_scanned": 0, "total_findings": 0, "fp_filtered": 0, "comment_posted": False}

    # 2. Python dosyalarını geçici dizine indir (Bandit için)
    with tempfile.TemporaryDirectory(prefix="pr_review_") as tmp_dir:
        import os as _os
        for path in py_files:
            content = await asyncio.to_thread(
                _download_file, owner, repo, path, head_sha, github_token or token
            )
            if not content:
                continue
            dest = _os.path.join(tmp_dir, path)
            _os.makedirs(_os.path.dirname(dest), exist_ok=True)
            try:
                with open(dest, "w", encoding="utf-8") as fh:
                    fh.write(content)
            except OSError:
                pass

        # 3. Bandit
        raw_bandit = await asyncio.to_thread(run_bandit_on_dir, tmp_dir)

        # 4. Semgrep (Docker varsa)
        raw_semgrep: list[dict] = []
        if is_docker_available():
            raw_semgrep = await asyncio.to_thread(run_semgrep, tmp_dir)

    # Tüm bulgular — CWE/OWASP zenginleştir
    all_raw = [enrich_finding(f) for f in (raw_bandit + raw_semgrep)]

    # 5. False Positive filtresi
    profile = {"language": "Python", "framework": ""}  # PR review sadece .py tarar
    genuine, fp_list = await filter_false_positives(all_raw, profile)

    # 6. Baseline karşılaştırması
    baseline = await asyncio.to_thread(_get_baseline_findings, repo_url)
    added, fixed = _compare_with_baseline(genuine, baseline, changed_set)

    # 7. Remediation önerileri (varsa — isteğe bağlı)
    try:
        from app.agents.remediation_agent import run_remediation
        await run_remediation(genuine, [], profile)
    except Exception:
        pass

    # 8. Markdown comment oluştur ve gönder
    if github_token:
        body = _build_comment(
            owner, repo, pr_number,
            genuine, fp_list,
            added, fixed,
            files_scanned=len(all_files),
        )
        posted = await asyncio.to_thread(
            _post_pr_comment, owner, repo, pr_number, body, github_token
        )
    else:
        logger.warning("[PRReview] GITHUB_TOKEN yok, comment gönderilmedi")
        posted = False

    result = {
        "files_scanned":   len(all_files),
        "total_findings":  len(genuine),
        "fp_filtered":     len(fp_list),
        "new_findings":    len(added),
        "fixed_findings":  len(fixed),
        "comment_posted":  posted,
    }
    logger.info("[PRReview] Tamamlandı: %s", result)
    return result
