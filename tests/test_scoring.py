"""Unit testler — app/scoring/scoring.py"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.scoring.scoring import calculate_score


def _full_analysis():
    return {"language": "Python", "framework": "FastAPI", "has_tests": True, "has_docker": True}


def _full_yaml_github():
    return """
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
"""


def test_perfect_score_github_actions():
    result = calculate_score(_full_analysis(), _full_yaml_github(), "github_actions")
    assert result["score"] == 100
    assert result["grade"] == "A"
    assert result["issues"] == []


def test_missing_tests():
    analysis = {**_full_analysis(), "has_tests": False}
    result = calculate_score(analysis, _full_yaml_github())
    assert result["score"] == 85       # 100 - 15
    assert result["grade"] == "B"
    assert any("test" in i.lower() for i in result["issues"])
    assert result["checks"]["tests"] is False


def test_missing_docker():
    analysis = {**_full_analysis(), "has_docker": False}
    result = calculate_score(analysis, _full_yaml_github())
    assert result["score"] == 90
    assert result["checks"]["docker"] is False


def test_unknown_language():
    analysis = {**_full_analysis(), "language": "unknown"}
    result = calculate_score(analysis, _full_yaml_github())
    assert result["checks"]["language_detected"] is False
    assert result["score"] == 85   # 100 - 15


def test_missing_trivy():
    yaml_no_trivy = _full_yaml_github().replace("aquasecurity/trivy-action@master", "").replace("scan-type: fs", "")
    result = calculate_score(_full_analysis(), yaml_no_trivy)
    assert result["checks"]["security_scan"] is False
    assert result["score"] == 75   # 100 - 25


def test_d_grade():
    result = calculate_score(
        {"language": "unknown", "framework": "unknown", "has_tests": False, "has_docker": False},
        "name: empty"
    )
    assert result["grade"] == "D"
    assert result["score"] < 60


def test_gitlab_ci_platform():
    gitlab_yaml = "stages:\n  - build\n  - test\n  - security\nbuild:\n  script:\n    - npm install\ntest:\n  script:\n    - npm test\ntrivy-scan:\n  script:\n    - trivy fs ."
    result = calculate_score(_full_analysis(), gitlab_yaml, "gitlab_ci")
    assert result["checks"]["checkout"] is True   # GitLab otomatik checkout
    assert result["platform"] == "gitlab_ci"


def test_jenkins_platform():
    jenkins_groovy = "pipeline { agent any stages { stage('Checkout') { steps { checkout scm } } stage('Build') { steps { sh 'npm install' } } stage('Test') { steps { sh 'npm test' } } stage('Security') { steps { sh 'trivy fs .' } } } }"
    result = calculate_score(_full_analysis(), jenkins_groovy, "jenkins")
    assert result["checks"]["checkout"] is True
    assert result["platform"] == "jenkins"


def test_score_bounds():
    """Skor 0-100 araliginda olmali."""
    result = calculate_score(
        {"language": "unknown", "framework": "unknown", "has_tests": False, "has_docker": False},
        ""
    )
    assert 0 <= result["score"] <= 100
