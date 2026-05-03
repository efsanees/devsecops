"""
GitHub reposunu ZIP olarak indirip geçici dizine açar.

Orchestrator (app/orchestrator.py) bunu bir kez çağırır ve
temp_dir yolunu state["temp_dir"] olarak tüm agent'lara geçirir.
Agent'lar state'de temp_dir yoksa kendi başlarına çağırabilir.

Dikkat: döndürülen temp_dir çağıranın sorumluluğundadır.
Orchestrator kullandıktan sonra shutil.rmtree(base_dir) ile siler.
"""

import io
import logging
import os
import re
import tempfile
import zipfile

import requests

logger = logging.getLogger(__name__)


def _parse_repo_path(repo_url: str) -> str:
    """'https://github.com/owner/repo' → 'owner/repo'"""
    match = re.search(r"github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)", repo_url)
    if not match:
        raise ValueError(f"Geçersiz GitHub URL: {repo_url}")
    return match.group(1).rstrip("/")


def download_repo(repo_url: str, token: str = "") -> tuple[str, str]:
    """
    Repoyu HEAD'den ZIP olarak indirir, geçici dizine açar.

    Returns:
        (repo_dir, base_dir)
        repo_dir: İçerik klasörü (doğrudan taranacak yol)
        base_dir: Ana temp klasörü (cleanup için: shutil.rmtree(base_dir))

    Raises:
        ValueError: Geçersiz URL
        requests.HTTPError: İndirme başarısız
    """
    repo_path = _parse_repo_path(repo_url)
    zip_url = f"https://api.github.com/repos/{repo_path}/zipball/HEAD"
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    logger.info("Repo indiriliyor: %s", zip_url)
    try:
        response = requests.get(zip_url, headers=headers, timeout=60, allow_redirects=True)
    except requests.Timeout:
        raise RuntimeError("Repo indirme zaman aşımına uğradı (60s). GitHub erişilebilir mi?")
    except requests.ConnectionError:
        raise RuntimeError("GitHub'a bağlanılamadı. İnternet bağlantısını kontrol et.")

    if response.status_code == 404:
        hint = " Token gerekebilir (özel repo)." if not token else ""
        raise RuntimeError(f"Repo bulunamadı: {repo_path}.{hint}")
    if response.status_code == 403:
        raise RuntimeError(f"GitHub erişim reddedildi (403). Rate limit veya yetki sorunu.")
    if response.status_code == 401:
        raise RuntimeError("GitHub token geçersiz veya süresi dolmuş.")
    response.raise_for_status()

    base_dir = tempfile.mkdtemp(prefix="devsecops_")
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(base_dir)

    # GitHub ZIP'i {owner}-{repo}-{sha}/ alt klasörüne çıkarır
    sub_dirs = [
        d for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
    ]
    repo_dir = os.path.join(base_dir, sub_dirs[0]) if sub_dirs else base_dir

    logger.info("Repo açıldı: %s", repo_dir)
    return repo_dir, base_dir
