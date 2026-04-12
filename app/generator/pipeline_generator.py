import os
import logging
from groq import Groq
from fastapi import HTTPException
from app.analyzer.repo_analyzer import detect_commands
from app.utils.yaml_utils import clean_yaml_output, validate_yaml

logger = logging.getLogger(__name__)


def generate_pipeline(analysis: dict, context: list, max_retries: int = 3) -> str:
    build_cmd, test_cmd = detect_commands(analysis)
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    prompt = f"""You are a DevSecOps engineer. Generate a complete and valid GitHub Actions YAML pipeline.

Project info:
- Language: {analysis["language"]}
- Framework: {analysis.get("framework", "unknown")}
- Has Docker: {analysis["has_docker"]}
- Has Tests: {analysis["has_tests"]}
- Files: {context[:100]}

Commands to use:
- Build: {build_cmd}
- Test: {test_cmd}

REQUIRED steps (all must be present):
1. actions/checkout step
2. Language setup step (setup-node / setup-python / setup-dotnet)
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
        logger.info(f"Pipeline üretiliyor (deneme {attempt}/{max_retries})")
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048
            )
            result = clean_yaml_output(response.choices[0].message.content)

            if validate_yaml(result):
                logger.info("Geçerli YAML üretildi")
                return result

            logger.warning(f"Deneme {attempt}: Geçersiz YAML, tekrar deneniyor")

        except Exception as e:
            logger.error(f"Deneme {attempt} hatası: {e}")

    raise HTTPException(status_code=500, detail=f"{max_retries} denemede geçerli YAML üretilemedi")
