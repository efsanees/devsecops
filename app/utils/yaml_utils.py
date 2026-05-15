import yaml


def clean_yaml_output(text: str) -> str:
    """LLM çıktısından markdown code-fence'leri ayıklayıp temiz YAML döner."""
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
