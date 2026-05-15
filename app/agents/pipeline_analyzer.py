"""
Pipeline Analyzer Agent — repodaki mevcut CI/CD dosyalarını okur, eksik
güvenlik adımlarını tespit eder.

Desteklenen platformlar:
  - GitHub Actions  (.github/workflows/*.yml / *.yaml)
  - GitLab CI       (.gitlab-ci.yml)
  - Jenkins         (Jenkinsfile) — Groovy, regex tabanlı
  - Azure DevOps    (azure-pipelines.yml)
  - Bitbucket       (bitbucket-pipelines.yml)

Her pipeline için 9 adım kategorisi kontrol edilir:
  checkout, build, test, lint, sast, sca, secret_scan, container_scan, deploy

Sonuç:
  existing_pipelines: bulunan pipeline'ların özeti
  missing_steps:      tüm pipeline'larda eksik kalan kategoriler
  coverage_score:     0-100, bulunan kategori sayısı / 9
"""

import asyncio
import logging
import os
import re
from typing import Any

import yaml

from app.agents.base import Agent, AgentResult
from app.github.github_service import get_file_content

logger = logging.getLogger(__name__)

# Her kategori için aranacak anahtar kelimeler.
# Hem 'uses:' değerlerinde hem 'run:' komutlarında hem 'name:' alanlarında aranır.
STEP_KEYWORDS: dict[str, list[str]] = {
    "checkout":       ["checkout", "actions/checkout"],
    "build":          ["build", "install", "compile", "npm ci", "npm install",
                       "pip install", "mvn package", "gradle build",
                       "cargo build", "dotnet build", "composer install",
                       "bundle install", "go build"],
    "test":           ["test", "pytest", "jest", "mocha", "vitest", "rspec",
                       "phpunit", "cargo test", "go test", "dotnet test",
                       "mvn test", "mvn verify", "gradle test"],
    "lint":           ["lint", "flake8", "eslint", "pylint", "rubocop",
                       "golangci", "clippy", "super-linter", "reviewdog"],
    "sast":           ["sast", "semgrep", "bandit", "codeql", "sonar",
                       "checkmarx", "veracode", "fortify", "snyk code",
                       "psalm", "phpstan", "gosec"],
    "sca":            ["sca", "trivy", "snyk", "dependency-check",
                       "dependabot", "safety", "npm audit", "owasp",
                       "retire.js", "osvscanner", "grype"],
    "secret_scan":    ["gitleaks", "trufflehog", "detect-secrets",
                       "secretlint", "secret-scan", "credential"],
    "container_scan": ["container", "grype", "anchore", "docker scan",
                       "aquasec", "trivy image", "sysdig"],
    "deploy":         ["deploy", "release", "publish", "helm upgrade",
                       "kubectl apply", "terraform apply", "heroku",
                       "vercel", "netlify", "firebase deploy"],
}

ALL_CATEGORIES = list(STEP_KEYWORDS.keys())

# CI/CD dosya tanıma kalıpları: (path_pattern, platform_adı)
PIPELINE_PATTERNS: list[tuple[str, str]] = [
    (r"\.github/workflows/[^/]+\.ya?ml$",  "github_actions"),
    (r"(^|/)\.gitlab-ci\.ya?ml$",          "gitlab_ci"),
    (r"(^|/)Jenkinsfile$",                 "jenkins"),
    (r"(^|/)azure-pipelines\.ya?ml$",      "azure_devops"),
    (r"(^|/)bitbucket-pipelines\.ya?ml$",  "bitbucket"),
]


def _detect_pipeline_files(file_list: list[str]) -> list[tuple[str, str]]:
    """Dosya listesinden CI/CD dosyalarını döndürür: [(path, platform), ...]"""
    found = []
    for path in file_list:
        for pattern, platform in PIPELINE_PATTERNS:
            if re.search(pattern, path):
                found.append((path, platform))
                break
    return found


def _collect_text_tokens(obj: Any) -> list[str]:
    """
    YAML'dan parse edilmiş herhangi bir yapıdan (dict/list/str)
    tüm string değerleri düz liste olarak toplar.
    Anahtar kelime araması için kullanılır.
    """
    tokens: list[str] = []
    if isinstance(obj, str):
        tokens.append(obj.lower())
    elif isinstance(obj, list):
        for item in obj:
            tokens.extend(_collect_text_tokens(item))
    elif isinstance(obj, dict):
        for v in obj.values():
            tokens.extend(_collect_text_tokens(v))
    return tokens


def _analyze_yaml_pipeline(content: str) -> dict[str, bool]:
    """
    YAML pipeline içeriğini analiz eder.
    Döner: {kategori: True/False} — adım bulundu mu?
    """
    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.warning("YAML parse hatası: %s", e)
        parsed = None

    # Parse başarısız olursa düz metin araması yap
    text_to_search = " ".join(_collect_text_tokens(parsed)) if parsed else content.lower()

    result = {}
    for category, keywords in STEP_KEYWORDS.items():
        result[category] = any(kw in text_to_search for kw in keywords)
    return result


def _analyze_jenkinsfile(content: str) -> dict[str, bool]:
    """
    Groovy Jenkinsfile için regex tabanlı analiz.
    YAML değil, stage isimlerine ve sh() çağrılarına bakılır.
    """
    content_lower = content.lower()
    result = {}
    for category, keywords in STEP_KEYWORDS.items():
        result[category] = any(kw in content_lower for kw in keywords)
    return result


def _missing_steps(detected: dict[str, bool]) -> list[str]:
    return [cat for cat, found in detected.items() if not found]


def _coverage_score(detected: dict[str, bool]) -> int:
    found_count = sum(1 for v in detected.values() if v)
    return round(found_count / len(ALL_CATEGORIES) * 100)


class PipelineAnalyzerAgent(Agent):
    name = "pipeline_analyzer"

    async def run(self, state: dict) -> AgentResult:
        repo_url = state["repo_url"]
        token = state.get("token", "")
        file_list = state.get("file_list", [])

        logger.info("[PipelineAnalyzer] Başlıyor")

        pipeline_files = _detect_pipeline_files(file_list)

        if not pipeline_files:
            logger.info("[PipelineAnalyzer] CI/CD dosyası bulunamadı")
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={
                    "existing_pipelines": [],
                    "missing_steps": ALL_CATEGORIES,
                    "coverage_score": 0,
                    "has_pipeline": False,
                },
                findings=_build_findings([], ALL_CATEGORIES),
            )

        existing_pipelines = []
        # Tüm platformlardaki adımların birleşik tespiti (en kapsamlı sonuç)
        combined_detected: dict[str, bool] = {cat: False for cat in ALL_CATEGORIES}

        temp_dir = state.get("temp_dir")

        for path, platform in pipeline_files:
            logger.info("[PipelineAnalyzer] Analiz ediliyor: %s (%s)", path, platform)

            content: str | None = None
            # Prefer already-downloaded repo to avoid GitHub API rate limits
            if temp_dir:
                local_path = os.path.join(temp_dir, path.replace("/", os.sep))
                try:
                    with open(local_path, encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                except OSError:
                    pass

            if not content:
                content = await asyncio.to_thread(get_file_content, repo_url, token, path)

            if not content:
                logger.warning("[PipelineAnalyzer] İçerik alınamadı: %s", path)
                continue

            if platform == "jenkins":
                detected = _analyze_jenkinsfile(content)
            else:
                detected = _analyze_yaml_pipeline(content)

            # Birleşik: herhangi bir pipeline'da varsa "var" say
            for cat, found in detected.items():
                if found:
                    combined_detected[cat] = True

            existing_pipelines.append({
                "path": path,
                "platform": platform,
                "detected_steps": [cat for cat, found in detected.items() if found],
                "missing_steps": _missing_steps(detected),
                "coverage_score": _coverage_score(detected),
            })

        missing = _missing_steps(combined_detected)
        score = _coverage_score(combined_detected)

        logger.info(
            "[PipelineAnalyzer] Tamamlandı: %d pipeline, skor %d/100, %d eksik adım",
            len(existing_pipelines), score, len(missing),
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "existing_pipelines": existing_pipelines,
                "missing_steps": missing,
                "coverage_score": score,
                "has_pipeline": len(existing_pipelines) > 0,
            },
            findings=_build_findings(existing_pipelines, missing),
        )


def _build_findings(
    pipelines: list[dict],
    missing: list[str],
) -> list[dict]:
    """
    Eksik güvenlik adımlarını standart finding formatına çevirir.
    LLM reasoner ve DSOMM scorer bu listeyi tüketir.
    """
    findings = []

    if not pipelines:
        findings.append({
            "type": "missing_pipeline",
            "severity": "HIGH",
            "title": "CI/CD pipeline bulunamadı",
            "description": "Repoda hiç CI/CD konfigürasyonu yok. "
                           "Otomatik build, test ve güvenlik taraması yapılmıyor.",
            "recommendation": "Önerilen GitHub Actions pipeline'ını .github/workflows/ altına ekle.",
        })
        return findings

    security_steps = {"sast", "sca", "secret_scan", "container_scan"}
    missing_security = security_steps & set(missing)

    severity_map = {
        "sast":           ("HIGH",   "Statik kod analizi (SAST) adımı eksik"),
        "sca":            ("HIGH",   "Bağımlılık güvenlik taraması (SCA) adımı eksik"),
        "secret_scan":    ("HIGH",   "Secret/credential tarama adımı eksik"),
        "container_scan": ("MEDIUM", "Container güvenlik taraması adımı eksik"),
        "test":           ("MEDIUM", "Otomatik test adımı eksik"),
        "lint":           ("LOW",    "Linting adımı eksik"),
    }

    for step in missing:
        if step in severity_map:
            severity, title = severity_map[step]
            findings.append({
                "type": "missing_pipeline_step",
                "severity": severity,
                "title": title,
                "missing_step": step,
                "recommendation": f"Pipeline'a '{step}' adımı ekle.",
            })

    return findings
