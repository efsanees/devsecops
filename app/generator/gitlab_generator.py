"""
GitLab CI Pipeline Generator — Template tabanlı (LLM kullanılmaz)
"""

from app.analyzer.repo_analyzer import detect_commands

_DOCKER_IMAGE = {
    "Node.js":       "node:20-alpine",
    "Python":        "python:3.11-slim",
    ".NET":          "mcr.microsoft.com/dotnet/sdk:8.0",
    "Java (Maven)":  "maven:3.9-eclipse-temurin-17",
    "Java (Gradle)": "gradle:8-jdk17",
    "Go":            "golang:1.22-alpine",
    "Rust":          "rust:1.77-slim",
}

_CACHE_PATHS = {
    "Node.js":       ["node_modules/"],
    "Python":        [".cache/pip"],
    "Java (Maven)":  [".m2/repository"],
    "Java (Gradle)": [".gradle/caches"],
    "Go":            ["$GOPATH/pkg/mod"],
    "Rust":          ["target/"],
}


def generate_gitlab_pipeline(analysis: dict) -> str:
    lang = analysis.get("language", "unknown")
    has_docker = analysis.get("has_docker", False)
    build_cmd, test_cmd = detect_commands(analysis)
    image = _DOCKER_IMAGE.get(lang, "ubuntu:22.04")
    cache_paths = _CACHE_PATHS.get(lang, [])

    cache_block = ""
    if cache_paths:
        paths_yaml = "\n".join(f"    - {p}" for p in cache_paths)
        cache_block = f"""  cache:
    paths:
{paths_yaml}
"""

    docker_stage = ""
    docker_job = ""
    if has_docker:
        docker_stage = "\n  - docker"
        docker_job = """
docker-build:
  stage: docker
  image: docker:24
  services:
    - docker:24-dind
  variables:
    DOCKER_TLS_CERTDIR: ""
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA .
  only:
    - main
    - master
"""

    pipeline = f"""# DevSecOps AI tarafindan uretildi
stages:
  - build
  - test
  - security{docker_stage}

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

# --- Build ---
build:
  stage: build
  image: {image}
{cache_block}  script:
    - {build_cmd}
  artifacts:
    paths:
      - .
    expire_in: 1 hour

# --- Test ---
test:
  stage: test
  image: {image}
{cache_block}  script:
    - {test_cmd}
  artifacts:
    reports:
      junit: "**/test-results/*.xml"
    when: always
{docker_job}
# --- Security: Trivy ---
trivy-scan:
  stage: security
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  script:
    - trivy fs --severity CRITICAL,HIGH --exit-code 0 --no-progress .
  allow_failure: true
  artifacts:
    reports:
      sast: trivy-report.json
    when: always

# --- Security: Secrets ---
secrets-scan:
  stage: security
  image: zricethezav/gitleaks:latest
  script:
    - gitleaks detect --source . --exit-code 0
  allow_failure: true
"""
    return pipeline.strip()
