from fastapi import FastAPI
import requests
import yaml
import base64

app = FastAPI()

# -----------------------------
# GitHub'dan dosya çek
# -----------------------------
def get_repo_files(repo_url, token=""):
    api_url = repo_url.replace("github.com", "api.github.com/repos") + "/contents"

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(api_url, headers=headers)

    if response.status_code != 200:
        return {"error": response.text}

    return response.json()


# -----------------------------
# Tek dosya içeriği çek
# -----------------------------
def get_file_content(repo_url, token, filename):
    repo_path = repo_url.replace("https://github.com/", "")
    api_url = f"https://api.github.com/repos/{repo_path}/contents/{filename}"

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(api_url, headers=headers)

    if response.status_code != 200:
        return None

    data = response.json()
    content = base64.b64decode(data["content"]).decode()
    return content


# -----------------------------
# Repo analiz
# -----------------------------
def analyze_repo(repo_url, token=""):
    files = get_repo_files(repo_url, token)

    if isinstance(files, dict) and "error" in files:
        return {"language": "unknown", "has_tests": False}

    file_names = [f.get("name", "") for f in files]

    result = {
        "language": "unknown",
        "framework": "unknown",
        "has_tests": False,
        "has_docker": False
    }

    if "package.json" in file_names:
        result["language"] = "Node.js"

        content = get_file_content(repo_url, token, "package.json")

        if content:
            if "react" in content.lower():
                result["framework"] = "React"

            if "next" in content.lower():
                result["framework"] = "Next.js"

            if "jest" in content.lower():
                result["has_tests"] = True

    if "requirements.txt" in file_names:
        result["language"] = "Python"
        result["has_tests"] = True

    if "Dockerfile" in file_names:
        result["has_docker"] = True

    return result


# -----------------------------
# Komut belirleme
# -----------------------------
def detect_commands(analysis):
    if analysis["language"] == "Node.js":
        build = "npm install"
        test = "npm test" if analysis["has_tests"] else "echo no tests"

    elif analysis["language"] == "Python":
        build = "pip install -r requirements.txt"
        test = "pytest" if analysis["has_tests"] else "echo no tests"

    else:
        build = "echo build step"
        test = "echo test step"

    return build, test


# -----------------------------
# Pipeline üret (Ollama)
# -----------------------------
def generate_pipeline(repo_url, token, context):
    try:
        analysis = analyze_repo(repo_url, token)
        build_cmd, test_cmd = detect_commands(analysis)

        prompt = f"""
Generate ONLY a valid GitHub Actions YAML pipeline.

Project files:
{context}

Use these commands:
Build: {build_cmd}
Test: {test_cmd}

Include Trivy security scan.

Rules:
- Only YAML
- No explanation
- No markdown
"""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        data = response.json()
        return data.get("response", "")

    except Exception as e:
        return f"Ollama Error: {str(e)}"


# -----------------------------
# YAML temizleme
# -----------------------------
def clean_yaml_output(text):
    if "```yaml" in text:
        text = text.split("```yaml")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1]

    return text.strip()


# -----------------------------
# YAML doğrulama
# -----------------------------
def validate_yaml(yaml_text):
    try:
        yaml.safe_load(yaml_text)
        return True
    except:
        return False


# -----------------------------
# GitHub'a push
# -----------------------------
def push_to_github(repo_url, token, yaml_content):
    repo_path = repo_url.replace("https://github.com/", "")
    api_url = f"https://api.github.com/repos/{repo_path}/contents/.github/workflows/main.yml"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    # varsa güncelle
    get_resp = requests.get(api_url, headers=headers)
    sha = None
    if get_resp.status_code == 200:
        sha = get_resp.json()["sha"]

    encoded_content = base64.b64encode(yaml_content.encode()).decode()

    data = {
        "message": "Add DevSecOps pipeline",
        "content": encoded_content
    }

    if sha:
        data["sha"] = sha

    response = requests.put(api_url, headers=headers, json=data)

    return response.json()


# -----------------------------
# API
# -----------------------------
@app.get("/")
def home():
    return {"message": "DevSecOps AI çalışıyor"}


@app.post("/analyze")
def analyze(repo_url: str, token: str = ""):
    return analyze_repo(repo_url, token)


@app.post("/auto")
def auto(repo_url: str, token: str = ""):
    files = get_repo_files(repo_url, token)

    if isinstance(files, dict) and "error" in files:
        context = ["empty repo"]
    else:
        context = [f.get("name", "") for f in files]

    yaml_text = generate_pipeline(repo_url, token, context)
    yaml_text = clean_yaml_output(yaml_text)

    return {"pipeline": yaml_text}


@app.post("/auto-push")
def auto_push(repo_url: str, token: str):
    files = get_repo_files(repo_url, token)

    if isinstance(files, dict) and "error" in files:
        context = ["empty repo"]
    else:
        context = [f.get("name", "") for f in files]

    yaml_text = generate_pipeline(repo_url, token, context)
    yaml_text = clean_yaml_output(yaml_text)

    result = push_to_github(repo_url, token, yaml_text)

    return {
        "pipeline": yaml_text,
        "github_response": result
    }