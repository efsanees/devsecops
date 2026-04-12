import json
import logging
from app.github.github_service import get_all_files, get_repo_files, get_file_content, find_file_path

logger = logging.getLogger(__name__)


def analyze_repo(repo_url: str, token: str = "") -> dict:
    logger.info(f"Repo analiz ediliyor: {repo_url}")

    all_files = get_all_files(repo_url, token)

    # Rate limit veya hata durumunda root'a fallback
    if not all_files:
        logger.warning("Recursive analiz başarısız, root'a fallback yapılıyor")
        root = get_repo_files(repo_url, token)
        if isinstance(root, list):
            all_files = [f.get("path", f.get("name", "")) for f in root]

    if not all_files:
        logger.warning("Dosya listesi boş veya repo erişilemiyor")
        return {
            "language": "unknown",
            "framework": "unknown",
            "has_tests": False,
            "has_docker": False
        }

    logger.info(f"Toplam {len(all_files)} dosya bulundu")

    result = {
        "language": "unknown",
        "framework": "unknown",
        "has_tests": False,
        "has_docker": False
    }

    # Test dosyası tespiti (alt klasörler dahil)
    has_test_files = any(
        ("test_" in f or "_test" in f or "spec" in f.lower())
        and f.endswith((".py", ".js", ".ts", ".cs"))
        for f in all_files
    )

    # Node.js
    pkg_path = find_file_path(all_files, "package.json")
    if pkg_path:
        result["language"] = "Node.js"
        content = get_file_content(repo_url, token, pkg_path)
        if content:
            try:
                pkg = json.loads(content)
                all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                dep_names = [d.lower() for d in all_deps.keys()]

                if "react" in dep_names or "react-dom" in dep_names:
                    result["framework"] = "React"
                elif "next" in dep_names:
                    result["framework"] = "Next.js"
                elif "vue" in dep_names:
                    result["framework"] = "Vue"
                elif "express" in dep_names:
                    result["framework"] = "Express"
                elif "@angular/core" in dep_names:
                    result["framework"] = "Angular"

                if any(d in dep_names for d in ["jest", "mocha", "vitest", "jasmine"]):
                    result["has_tests"] = True

            except Exception as e:
                logger.error(f"package.json parse hatası: {e}")

        if has_test_files:
            result["has_tests"] = True

    # Python
    req_path = find_file_path(all_files, "requirements.txt")
    if req_path:
        result["language"] = "Python"
        req_content = get_file_content(repo_url, token, req_path)
        if req_content and "pytest" in req_content.lower():
            result["has_tests"] = True
        if has_test_files:
            result["has_tests"] = True

    # .NET
    if any(f.endswith(".csproj") for f in all_files) or any(f.endswith(".sln") for f in all_files):
        result["language"] = ".NET"
        result["has_tests"] = (
            any("test" in f.lower() for f in all_files if f.endswith(".csproj"))
            or has_test_files
        )

    # Docker
    if find_file_path(all_files, "Dockerfile") or find_file_path(all_files, "docker-compose.yml"):
        result["has_docker"] = True

    logger.info(f"Analiz sonucu: {result}")
    return result


def detect_commands(analysis: dict) -> tuple[str, str]:
    lang = analysis["language"]

    if lang == "Node.js":
        return "npm install", "npm test" if analysis["has_tests"] else "echo no tests"
    elif lang == "Python":
        return "pip install -r requirements.txt", "pytest" if analysis["has_tests"] else "echo no tests"
    elif lang == ".NET":
        return "dotnet build", "dotnet test" if analysis["has_tests"] else "echo no tests"
    else:
        return "echo build step", "echo test step"
