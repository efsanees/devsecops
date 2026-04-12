import requests
import base64
import logging
import time

logger = logging.getLogger(__name__)


def get_repo_files(repo_url: str, token: str = "") -> list | dict:
    api_url = repo_url.replace("github.com", "api.github.com/repos") + "/contents"
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    response = requests.get(api_url, headers=headers, timeout=10)

    if response.status_code != 200:
        return {"error": response.text}

    return response.json()


def get_all_files(repo_url: str, token: str = "", path: str = "", depth: int = 0, max_depth: int = 3) -> list:
    if depth > max_depth:
        return []

    api_url = repo_url.replace("github.com", "api.github.com/repos") + f"/contents/{path}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        time.sleep(0.1)  # Rate limit koruması
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []

        items = response.json()
        if not isinstance(items, list):
            return []

        all_files = []
        for item in items:
            if item.get("type") == "file":
                all_files.append(item.get("path", ""))  # name değil, path
            elif item.get("type") == "dir":
                sub_files = get_all_files(repo_url, token, item.get("path", ""), depth + 1, max_depth)
                all_files.extend(sub_files)

        return all_files

    except Exception as e:
        logger.error(f"get_all_files hatası ({path}): {e}")
        return []


def get_file_content(repo_url: str, token: str, filepath: str) -> str | None:
    """filepath: tam yol (ör: src/requirements.txt)"""
    repo_path = repo_url.replace("https://github.com/", "")
    api_url = f"https://api.github.com/repos/{repo_path}/contents/{filepath}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None

        data = response.json()
        return base64.b64decode(data["content"]).decode()

    except Exception as e:
        logger.error(f"get_file_content hatası ({filepath}): {e}")
        return None


def find_file_path(files: list, target: str) -> str | None:
    """Herhangi bir klasörde target ile biten dosyayı bulur."""
    for f in files:
        if f.endswith(target):
            return f
    return None


def push_to_github(repo_url: str, token: str, yaml_content: str) -> dict:
    repo_path = repo_url.replace("https://github.com/", "")
    api_url = f"https://api.github.com/repos/{repo_path}/contents/.github/workflows/devsecops.yml"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    get_resp = requests.get(api_url, headers=headers)
    sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None

    data = {
        "message": "chore: add DevSecOps pipeline via AI",
        "content": base64.b64encode(yaml_content.encode()).decode()
    }
    if sha:
        data["sha"] = sha

    response = requests.put(api_url, headers=headers, json=data)
    return response.json()
