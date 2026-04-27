"""
Docker tabanlı güvenlik tarayıcıları için ortak subprocess wrapper.

Her runner (semgrep_runner, trivy_runner, gitleaks_runner) bu modüldeki
run_docker_tool() fonksiyonunu kullanır.

Windows not: Docker Desktop, host path'i /c/users/... formatında bekler.
_to_docker_path() bu dönüşümü otomatik yapar.
"""

import json
import logging
import platform
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300  # 5 dakika


def _to_docker_path(host_path: str) -> str:
    """
    Windows path'ini Docker volume mount için uygun formata çevirir.
    Örnek: C:\\Users\\foo\\tmp  →  /c/Users/foo/tmp
    Linux/macOS'ta değişiklik yapmaz.
    """
    if platform.system() != "Windows":
        return host_path

    p = Path(host_path)
    parts = p.parts  # ('C:\\', 'Users', 'foo', 'tmp')
    drive = parts[0].rstrip("\\:").lower()  # 'c'
    rest = "/".join(parts[1:])              # 'Users/foo/tmp'
    return f"/{drive}/{rest}"


def run_docker_tool(
    image: str,
    repo_dir: str,
    extra_args: list[str],
    timeout: int = DEFAULT_TIMEOUT,
) -> dict | list:
    """
    Docker container'ı çalıştırır, stdout'tan JSON döner.

    Args:
        image:      Docker imaj adı, örn. "semgrep/semgrep:latest"
        repo_dir:   Taranacak repo'nun host üzerindeki mutlak yolu.
        extra_args: İmaj adından sonra gelecek ek argümanlar.
        timeout:    Saniye cinsinden maksimum çalışma süresi.

    Returns:
        JSON olarak parse edilmiş dict veya list.

    Raises:
        subprocess.TimeoutExpired: Timeout aşılırsa.
        RuntimeError: Container sıfır dışı exit code ile çıkarsa.
        json.JSONDecodeError: Çıktı geçerli JSON değilse.
    """
    docker_path = _to_docker_path(repo_dir)
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{docker_path}:/src",
        image,
        *extra_args,
    ]

    logger.info("Docker komutu: %s", " ".join(cmd))

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if proc.returncode not in (0, 1):
        # Semgrep ve Gitleaks finding varsa exit 1 döner — bu normal.
        # Gerçek hata exit 2+ demek.
        raise RuntimeError(
            f"{image} exit {proc.returncode}:\n{proc.stderr[:500]}"
        )

    stdout = proc.stdout.strip()
    if not stdout:
        logger.warning("%s stdout boş döndü", image)
        return {}

    return json.loads(stdout)


def is_docker_available() -> bool:
    """Docker daemon'ın erişilebilir olup olmadığını kontrol eder."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
