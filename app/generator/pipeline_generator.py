"""
Pipeline Generator — GitHub Actions (LLM), GitLab CI ve Jenkins (template)
"""

import os
import logging
from groq import Groq
from fastapi import HTTPException
from app.analyzer.repo_analyzer import detect_commands
from app.utils.yaml_utils import clean_yaml_output, validate_yaml
from app.generator.gitlab_generator import generate_gitlab_pipeline
from app.generator.jenkins_generator import generate_jenkins_pipeline

logger = logging.getLogger(__name__)


def generate_pipeline(
    analysis: dict,
    context: list,
    platform: str = "github_actions",
    max_retries: int = 3,
) -> str:
    """
    Platform'a gore dogru ureticiyi cagirır.
    - github_actions: Groq LLM (llama-3.3-70b-versatile)
    - gitlab_ci:      Template tabanlı
    - jenkins:        Template tabanlı
    """
    if platform == "gitlab_ci":
        logger.info("GitLab CI pipeline uretiliyor (template)")
        return generate_gitlab_pipeline(analysis)

    if platform == "jenkins":
        logger.info("Jenkins pipeline uretiliyor (template)")
        return generate_jenkins_pipeline(analysis)

    # GitHub Actions — Groq LLM
    return _generate_github_actions(analysis, context, max_retries)


def _generate_github_actions(analysis: dict, context: list, max_retries: int) -> str:
    build_cmd, test_cmd = detect_commands(analysis)
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    prompt = f"""You are a DevSecOps engineer. Generate a complete and valid GitHub Actions YAML pipeline.

Project info:
- Language: {analysis["language"]}
- Framework: {analysis.get("framework", "unknown")}
- Has Docker: {analysis["has_docker"]}
- Has Tests: {analysis["has_tests"]}
- Files: {[f for f in context if not f.startswith(('.github/', 'scripts/'))][:80]}

Commands to use:
- Build: {build_cmd}
- Test: {test_cmd}

REQUIRED steps (all must be present):
1. actions/checkout step
2. Language setup step (setup-node / setup-python / setup-dotnet / setup-java / setup-go)
3. Build step
4. Test step
5. Trivy security scan step (aquasecurity/trivy-action)

OUTPUT RULES:
- Output ONLY valid YAML
- No markdown, no explanation, no code blocks
- Start directly with "name:"
- The pipeline MUST include Trivy scan
"""

    for attempt in range(1, max_retries + 1):
        logger.info(f"GitHub Actions pipeline uretiliyor (deneme {attempt}/{max_retries})")
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            result = clean_yaml_output(response.choices[0].message.content)
            if validate_yaml(result):
                logger.info("Gecerli YAML uretildi")
                return result
            logger.warning(f"Deneme {attempt}: Gecersiz YAML")
        except Exception as e:
            logger.error(f"Deneme {attempt} hatasi: {e}")

    raise HTTPException(status_code=500, detail=f"{max_retries} denemede gecerli YAML uretilemedi")
