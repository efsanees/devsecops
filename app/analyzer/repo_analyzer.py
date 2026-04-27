import json
import logging
from app.github.github_service import get_all_files, get_repo_files, get_file_content, find_file_path

logger = logging.getLogger(__name__)


def analyze_repo(repo_url: str, token: str = "") -> dict:
    logger.info(f"Repo analiz ediliyor: {repo_url}")

    all_files = get_all_files(repo_url, token)
    if not all_files:
        logger.warning("Recursive analiz basarisiz, root'a fallback")
        root = get_repo_files(repo_url, token)
        if isinstance(root, list):
            all_files = [f.get("path", f.get("name", "")) for f in root]

    if not all_files:
        logger.warning("Dosya listesi bos — token gerekebilir")
        return {"language": "unknown", "framework": "unknown", "has_tests": False, "has_docker": False}

    logger.info(f"Toplam {len(all_files)} dosya bulundu")

    result = {"language": "unknown", "framework": "unknown", "has_tests": False, "has_docker": False}

    has_test_files = any(
        ("test_" in f or "_test" in f or "spec" in f.lower())
        and f.endswith((".py", ".js", ".ts", ".cs", ".java", ".go", ".rs"))
        for f in all_files
    )

    # --- Node.js ---
    pkg_path = find_file_path(all_files, "package.json")
    if pkg_path:
        result["language"] = "Node.js"
        content = get_file_content(repo_url, token, pkg_path)
        if content:
            try:
                pkg = json.loads(content)
                all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                dep_names = [d.lower() for d in all_deps]
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
                elif "nuxt" in dep_names:
                    result["framework"] = "Nuxt"
                elif "svelte" in dep_names:
                    result["framework"] = "Svelte"
                if any(d in dep_names for d in ["jest", "mocha", "vitest", "jasmine", "cypress"]):
                    result["has_tests"] = True
            except Exception as e:
                logger.error(f"package.json parse hatasi: {e}")
        if has_test_files:
            result["has_tests"] = True

    # --- Python ---
    req_path = find_file_path(all_files, "requirements.txt")
    setup_py = find_file_path(all_files, "setup.py")
    pyproject = find_file_path(all_files, "pyproject.toml")
    if req_path or setup_py or pyproject:
        result["language"] = "Python"
        if req_path:
            req_content = get_file_content(repo_url, token, req_path)
            if req_content:
                if "pytest" in req_content.lower():
                    result["has_tests"] = True
                if "django" in req_content.lower():
                    result["framework"] = "Django"
                elif "flask" in req_content.lower():
                    result["framework"] = "Flask"
                elif "fastapi" in req_content.lower():
                    result["framework"] = "FastAPI"
        if has_test_files:
            result["has_tests"] = True

    # --- .NET ---
    if any(f.endswith(".csproj") for f in all_files) or any(f.endswith(".sln") for f in all_files):
        result["language"] = ".NET"
        result["has_tests"] = (
            any("test" in f.lower() for f in all_files if f.endswith(".csproj")) or has_test_files
        )

    # --- Java (Maven) ---
    pom_path = find_file_path(all_files, "pom.xml")
    if pom_path:
        result["language"] = "Java (Maven)"
        result["framework"] = "Spring" if any("spring" in f.lower() for f in all_files) else "unknown"
        result["has_tests"] = any(
            "test" in f.lower() for f in all_files if f.endswith(".java")
        ) or has_test_files

    # --- Java (Gradle) ---
    gradle_path = find_file_path(all_files, "build.gradle") or find_file_path(all_files, "build.gradle.kts")
    if gradle_path and "Java" not in result["language"]:
        result["language"] = "Java (Gradle)"
        result["has_tests"] = any(
            "test" in f.lower() for f in all_files if f.endswith(".java")
        ) or has_test_files

    # --- Go ---
    go_mod = find_file_path(all_files, "go.mod")
    if go_mod:
        result["language"] = "Go"
        result["has_tests"] = any(f.endswith("_test.go") for f in all_files)
        go_content = get_file_content(repo_url, token, go_mod)
        if go_content and "gin-gonic/gin" in go_content:
            result["framework"] = "Gin"
        elif go_content and "echo" in go_content:
            result["framework"] = "Echo"

    # --- Rust ---
    cargo_path = find_file_path(all_files, "Cargo.toml")
    if cargo_path:
        result["language"] = "Rust"
        result["has_tests"] = any(
            "tests/" in f or f.endswith("_test.rs") for f in all_files
        )
        cargo_content = get_file_content(repo_url, token, cargo_path)
        if cargo_content and "actix-web" in cargo_content:
            result["framework"] = "Actix"
        elif cargo_content and "axum" in cargo_content:
            result["framework"] = "Axum"

    # --- Docker ---
    if find_file_path(all_files, "Dockerfile") or find_file_path(all_files, "docker-compose.yml"):
        result["has_docker"] = True

    logger.info(f"Analiz sonucu: {result}")
    return result


def detect_commands(analysis: dict) -> tuple[str, str]:
    lang = analysis["language"]
    has_tests = analysis.get("has_tests", False)

    commands = {
        "Node.js":      ("npm install", "npm test" if has_tests else "echo 'test yok'"),
        "Python":       ("pip install -r requirements.txt", "pytest" if has_tests else "echo 'test yok'"),
        ".NET":         ("dotnet build", "dotnet test" if has_tests else "echo 'test yok'"),
        "Java (Maven)": ("mvn -B package --no-transfer-progress -DskipTests", "mvn test -B"),
        "Java (Gradle)":("gradle build -x test", "gradle test"),
        "Go":           ("go build ./...", "go test ./..."),
        "Rust":         ("cargo build --release", "cargo test"),
    }
    return commands.get(lang, ("echo 'build adimi'", "echo 'test adimi'"))
