import yaml
import logging

logger = logging.getLogger(__name__)

IGNORE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
                     ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3",
                     ".zip", ".tar", ".gz", ".pdf")


def clean_yaml_output(text: str) -> str:
    if "```yaml" in text:
        text = text.split("```yaml")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1]
    return text.strip()


def validate_yaml(yaml_text: str) -> bool:
    try:
        yaml.safe_load(yaml_text)
        return True
    except Exception:
        return False


def ensure_trivy(yaml_text: str) -> str:
    """Trivy yoksa parse ederek güvenli şekilde ekle."""
    if "trivy" in yaml_text.lower():
        return yaml_text

    logger.warning("Pipeline'da Trivy bulunamadı, ekleniyor")

    try:
        # Adım indentasyonunu mevcut YAML'dan tespit et
        indent = "      "  # GitHub Actions varsayılanı: 6 boşluk
        for line in yaml_text.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("- name:") or stripped.startswith("- uses:"):
                indent = " " * (len(line) - len(stripped))
                break

        trivy_block = (
            f"\n{indent}- name: Trivy security scan\n"
            f"{indent}  uses: aquasecurity/trivy-action@master\n"
            f"{indent}  with:\n"
            f"{indent}    scan-type: 'fs'\n"
            f"{indent}    scan-ref: '.'\n"
            f"{indent}    severity: 'CRITICAL,HIGH'\n"
        )
        result = yaml_text.rstrip() + trivy_block
        if validate_yaml(result):
            return result
    except Exception as e:
        logger.error(f"Trivy ekleme hatası: {e}")

    return yaml_text


def filter_context(all_files: list, limit: int = 100) -> list:
    """Binary/medya dosyalarını çıkar, limit uygula."""
    return [
        f for f in all_files
        if not f.lower().endswith(IGNORE_EXTENSIONS)
    ][:limit]
