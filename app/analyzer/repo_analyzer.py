import json
import logging
import os
from app.github.github_service import get_all_files, get_repo_files, get_file_content, find_file_path

logger = logging.getLogger(__name__)


def analyze_from_local_dir(repo_dir: str) -> dict:
    """
    İndirilmiş repo dizininden dil/framework/test/docker tespiti yapar.
    GitHub API başarısız olduğunda orchestrator tarafından fallback olarak çağrılır.
    """
    all_files = []
    for root, _dirs, files in os.walk(repo_dir):
        for fname in files:
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, repo_dir).replace("\\", "/")
            all_files.append(rel)

    if not all_files:
        return {"language": "unknown", "framework": "unknown",
                "has_tests": False, "has_docker": False,
                "package_manager": "unknown", "files": []}

    result = {
        "language": "unknown", "framework": "unknown",
        "has_tests": False, "has_docker": False,
        "package_manager": "unknown", "files": all_files,
    }

    has_test_files = any(
        ("test_" in f or "_test" in f or "spec" in f.lower())
        and f.endswith((".py", ".js", ".ts", ".cs", ".java", ".go", ".rs", ".rb", ".php"))
        for f in all_files
    )

    def _read(filename: str) -> str:
        path = find_file_path(all_files, filename)
        if path:
            try:
                with open(os.path.join(repo_dir, path), encoding="utf-8", errors="ignore") as fh:
                    return fh.read()
            except OSError:
                pass
        return ""

    # package.json → Node.js
    if find_file_path(all_files, "package.json"):
        result["language"] = "Node.js"
        result["package_manager"] = "npm"
        content = _read("package.json")
        try:
            pkg = json.loads(content)
            deps = [d.lower() for d in {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}]
            if "react" in deps or "react-dom" in deps:
                result["framework"] = "React"
            elif "next" in deps:
                result["framework"] = "Next.js"
            elif "vue" in deps:
                result["framework"] = "Vue"
            elif "express" in deps:
                result["framework"] = "Express"
            elif "@angular/core" in deps:
                result["framework"] = "Angular"
            if any(d in deps for d in ["jest", "mocha", "vitest", "jasmine", "cypress"]):
                result["has_tests"] = True
        except Exception:
            pass

    # Python
    if any(find_file_path(all_files, f) for f in ["requirements.txt", "setup.py", "pyproject.toml"]):
        result["language"] = "Python"
        result["package_manager"] = "pip"
        req = _read("requirements.txt")
        if req:
            if "pytest" in req.lower():
                result["has_tests"] = True
            if "django" in req.lower():
                result["framework"] = "Django"
            elif "flask" in req.lower():
                result["framework"] = "Flask"
            elif "fastapi" in req.lower():
                result["framework"] = "FastAPI"

    # .NET
    if any(f.endswith(".csproj") or f.endswith(".sln") for f in all_files):
        result["language"] = ".NET"
        result["package_manager"] = "nuget"

    # Java
    if find_file_path(all_files, "pom.xml"):
        result["language"] = "Java (Maven)"
        result["package_manager"] = "maven"
    elif find_file_path(all_files, "build.gradle"):
        result["language"] = "Java (Gradle)"
        result["package_manager"] = "gradle"

    # Go
    if find_file_path(all_files, "go.mod"):
        result["language"] = "Go"
        result["package_manager"] = "go modules"
        result["has_tests"] = any(f.endswith("_test.go") for f in all_files)

    # Rust
    if find_file_path(all_files, "Cargo.toml"):
        result["language"] = "Rust"
        result["package_manager"] = "cargo"

    # PHP
    if find_file_path(all_files, "composer.json"):
        result["language"] = "PHP"
        result["package_manager"] = "composer"

    # Ruby
    if find_file_path(all_files, "Gemfile"):
        result["language"] = "Ruby"
        result["package_manager"] = "bundler"

    # Dosya uzantısına göre son fallback
    if result["language"] == "unknown":
        ext_counts: dict[str, int] = {}
        for f in all_files:
            ext = os.path.splitext(f)[1].lower()
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
        ext_map = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".java": "Java", ".go": "Go", ".rs": "Rust", ".cs": ".NET",
            ".php": "PHP", ".rb": "Ruby", ".cpp": "C++", ".c": "C",
            ".kt": "Kotlin", ".swift": "Swift",
        }
        dominant = max(ext_counts, key=ext_counts.get) if ext_counts else ""
        if dominant in ext_map:
            result["language"] = ext_map[dominant]

    if has_test_files:
        result["has_tests"] = True
    if find_file_path(all_files, "Dockerfile") or find_file_path(all_files, "docker-compose.yml"):
        result["has_docker"] = True

    logger.info("[LocalProfiler] %s / %s (%d dosya)", result["language"], result["framework"], len(all_files))
    return result


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
        return {
            "language": "unknown", "framework": "unknown",
            "has_tests": False, "has_docker": False,
            "package_manager": "unknown", "files": [],
        }

    logger.info(f"Toplam {len(all_files)} dosya bulundu")

    result = {
        "language": "unknown",
        "framework": "unknown",
        "has_tests": False,
        "has_docker": False,
        "package_manager": "unknown",
        "files": all_files,   # orchestrator diğer agent'lara geçirir
    }

    has_test_files = any(
        ("test_" in f or "_test" in f or "spec" in f.lower())
        and f.endswith((".py", ".js", ".ts", ".cs", ".java", ".go", ".rs", ".rb", ".php"))
        for f in all_files
    )

    # --- Node.js ---
    pkg_path = find_file_path(all_files, "package.json")
    if pkg_path:
        result["language"] = "Node.js"
        result["package_manager"] = "npm"
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
                if find_file_path(all_files, "yarn.lock"):
                    result["package_manager"] = "yarn"
                elif find_file_path(all_files, "pnpm-lock.yaml"):
                    result["package_manager"] = "pnpm"
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
        result["package_manager"] = "pip"
        if find_file_path(all_files, "poetry.lock"):
            result["package_manager"] = "poetry"
        elif find_file_path(all_files, "Pipfile"):
            result["package_manager"] = "pipenv"
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
        result["package_manager"] = "nuget"
        result["has_tests"] = (
            any("test" in f.lower() for f in all_files if f.endswith(".csproj")) or has_test_files
        )

    # --- Java (Maven) ---
    pom_path = find_file_path(all_files, "pom.xml")
    if pom_path:
        result["language"] = "Java (Maven)"
        result["package_manager"] = "maven"
        result["framework"] = "Spring" if any("spring" in f.lower() for f in all_files) else "unknown"
        result["has_tests"] = any(
            "test" in f.lower() for f in all_files if f.endswith(".java")
        ) or has_test_files

    # --- Java (Gradle) ---
    gradle_path = find_file_path(all_files, "build.gradle") or find_file_path(all_files, "build.gradle.kts")
    if gradle_path and "Java" not in result["language"]:
        result["language"] = "Java (Gradle)"
        result["package_manager"] = "gradle"
        result["has_tests"] = any(
            "test" in f.lower() for f in all_files if f.endswith(".java")
        ) or has_test_files

    # --- Go ---
    go_mod = find_file_path(all_files, "go.mod")
    if go_mod:
        result["language"] = "Go"
        result["package_manager"] = "go modules"
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
        result["package_manager"] = "cargo"
        result["has_tests"] = any(
            "tests/" in f or f.endswith("_test.rs") for f in all_files
        )
        cargo_content = get_file_content(repo_url, token, cargo_path)
        if cargo_content and "actix-web" in cargo_content:
            result["framework"] = "Actix"
        elif cargo_content and "axum" in cargo_content:
            result["framework"] = "Axum"

    # --- PHP ---
    composer_path = find_file_path(all_files, "composer.json")
    if composer_path:
        result["language"] = "PHP"
        result["package_manager"] = "composer"
        result["has_tests"] = has_test_files or any(
            "phpunit" in f.lower() or "pest" in f.lower() for f in all_files
        )
        composer_content = get_file_content(repo_url, token, composer_path)
        if composer_content:
            try:
                comp = json.loads(composer_content)
                all_deps = {**comp.get("require", {}), **comp.get("require-dev", {})}
                dep_names = [d.lower() for d in all_deps]
                if "laravel/framework" in dep_names:
                    result["framework"] = "Laravel"
                elif "symfony/framework-bundle" in dep_names:
                    result["framework"] = "Symfony"
            except Exception as e:
                logger.error(f"composer.json parse hatasi: {e}")

    # --- Ruby ---
    gemfile_path = find_file_path(all_files, "Gemfile")
    if gemfile_path:
        result["language"] = "Ruby"
        result["package_manager"] = "bundler"
        result["has_tests"] = has_test_files or any(
            "spec" in f.lower() or "_test.rb" in f for f in all_files
        )
        gemfile_content = get_file_content(repo_url, token, gemfile_path)
        if gemfile_content:
            if "rails" in gemfile_content.lower():
                result["framework"] = "Rails"
            elif "sinatra" in gemfile_content.lower():
                result["framework"] = "Sinatra"

    # --- Docker ---
    if find_file_path(all_files, "Dockerfile") or find_file_path(all_files, "docker-compose.yml"):
        result["has_docker"] = True

    logger.info(f"Analiz sonucu: {result}")
    return result


def detect_commands(analysis: dict) -> tuple[str, str]:
    lang = analysis["language"]
    has_tests = analysis.get("has_tests", False)
    pkg = analysis.get("package_manager", "")

    commands = {
        "Node.js": (
            "pnpm install" if pkg == "pnpm" else "yarn install" if pkg == "yarn" else "npm install",
            "npm test" if has_tests else "echo 'test yok'",
        ),
        "Python": (
            "poetry install" if pkg == "poetry" else "pipenv install" if pkg == "pipenv" else "pip install -r requirements.txt",
            "pytest" if has_tests else "echo 'test yok'",
        ),
        ".NET":          ("dotnet build", "dotnet test" if has_tests else "echo 'test yok'"),
        "Java (Maven)":  ("mvn -B package --no-transfer-progress -DskipTests", "mvn verify -B"),
        "Java (Gradle)": ("gradle build -x test", "gradle test"),
        "Go":            ("go build ./...", "go test ./..."),
        "Rust":          ("cargo build --release", "cargo test"),
        "PHP":           ("composer install --no-interaction", "vendor/bin/phpunit" if has_tests else "echo 'test yok'"),
        "Ruby":          ("bundle install", "bundle exec rspec" if has_tests else "echo 'test yok'"),
    }
    return commands.get(lang, ("echo 'build adimi'", "echo 'test adimi'"))
