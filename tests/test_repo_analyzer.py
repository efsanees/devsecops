"""Unit testler — app/analyzer/repo_analyzer.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.analyzer.repo_analyzer import detect_commands
from app.security.sast_analyzer import _collect_python_files


class TestDetectCommands:
    def _analysis(self, lang, has_tests=True):
        return {"language": lang, "framework": "unknown", "has_tests": has_tests, "has_docker": False}

    def test_python_with_tests(self):
        b, t = detect_commands(self._analysis("Python", True))
        assert "pip install" in b
        assert "pytest" in t

    def test_python_no_tests(self):
        _, t = detect_commands(self._analysis("Python", False))
        assert "echo" in t

    def test_nodejs(self):
        b, t = detect_commands(self._analysis("Node.js"))
        assert "npm install" in b
        assert "npm test" in t

    def test_dotnet(self):
        b, t = detect_commands(self._analysis(".NET"))
        assert "dotnet build" in b
        assert "dotnet test" in t

    def test_java_maven(self):
        b, t = detect_commands(self._analysis("Java (Maven)"))
        assert "mvn" in b
        assert "mvn test" in t

    def test_java_gradle(self):
        b, t = detect_commands(self._analysis("Java (Gradle)"))
        assert "gradle build" in b
        assert "gradle test" in t

    def test_go(self):
        b, t = detect_commands(self._analysis("Go"))
        assert "go build" in b
        assert "go test" in t

    def test_rust(self):
        b, t = detect_commands(self._analysis("Rust"))
        assert "cargo build" in b
        assert "cargo test" in t

    def test_unknown_language_fallback(self):
        b, t = detect_commands(self._analysis("COBOL"))
        assert "echo" in b and "echo" in t


class TestCollectPythonFiles:
    def test_basic(self):
        files = ["app/main.py", "app/utils.py", "README.md"]
        result = _collect_python_files(files)
        assert "app/main.py" in result
        assert "README.md" not in result

    def test_exclude_venv(self):
        files = ["venv/lib/foo.py", ".venv/site-packages/bar.py", "app/main.py"]
        result = _collect_python_files(files)
        assert "app/main.py" in result
        assert not any("venv" in f for f in result)

    def test_exclude_migrations(self):
        files = ["migrations/0001_initial.py", "app/views.py"]
        result = _collect_python_files(files)
        assert "app/views.py" in result
        assert "migrations/0001_initial.py" not in result

    def test_manage_py_included(self):
        """manage.py guvenlik bulgulari icin taranmali."""
        files = ["manage.py", "app/views.py"]
        result = _collect_python_files(files)
        assert "manage.py" in result

    def test_test_files_last(self):
        files = ["app/views.py", "tests/test_views.py", "app/models.py"]
        result = _collect_python_files(files)
        src_idx = result.index("app/views.py")
        test_idx = result.index("tests/test_views.py")
        assert src_idx < test_idx

    def test_max_60_files(self):
        files = [f"module_{i}.py" for i in range(100)]
        result = _collect_python_files(files)
        assert len(result) == 60

    def test_empty_list(self):
        assert _collect_python_files([]) == []

    def test_no_py_files(self):
        assert _collect_python_files(["README.md", "package.json"]) == []
