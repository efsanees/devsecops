"""
Jenkins Declarative Pipeline Generator — Template tabanlı (LLM kullanılmaz)
"""

from app.analyzer.repo_analyzer import detect_commands

_AGENT_DOCKER = {
    "Node.js":       "node:20-alpine",
    "Python":        "python:3.11-slim",
    ".NET":          "mcr.microsoft.com/dotnet/sdk:8.0",
    "Java (Maven)":  "maven:3.9-eclipse-temurin-17",
    "Java (Gradle)": "gradle:8-jdk17",
    "Go":            "golang:1.22-alpine",
    "Rust":          "rust:1.77-slim",
}


def generate_jenkins_pipeline(analysis: dict) -> str:
    lang = analysis.get("language", "unknown")
    has_docker = analysis.get("has_docker", False)
    build_cmd, test_cmd = detect_commands(analysis)
    docker_image = _AGENT_DOCKER.get(lang, "ubuntu:22.04")

    docker_stage = ""
    if has_docker:
        docker_stage = """
        stage('Docker Build') {
            steps {
                script {
                    def img = docker.build("app:${env.BUILD_NUMBER}")
                    echo "Docker imaji olusturuldu: ${img.id}"
                }
            }
        }
"""

    pipeline = f"""// DevSecOps AI tarafindan uretildi
pipeline {{
    agent {{
        docker {{
            image '{docker_image}'
            args '-v /tmp:/tmp'
        }}
    }}

    options {{
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }}

    environment {{
        CI = 'true'
    }}

    stages {{
        stage('Checkout') {{
            steps {{
                checkout scm
            }}
        }}

        stage('Build') {{
            steps {{
                sh '{build_cmd}'
            }}
        }}

        stage('Test') {{
            steps {{
                sh '{test_cmd}'
            }}
            post {{
                always {{
                    junit allowEmptyResults: true, testResults: '**/test-results/*.xml'
                }}
            }}
        }}
{docker_stage}
        stage('Security: Trivy') {{
            steps {{
                sh '''
                    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
                    trivy fs --severity CRITICAL,HIGH --exit-code 0 --no-progress .
                '''
            }}
            post {{
                always {{
                    archiveArtifacts allowEmptyArchive: true, artifacts: 'trivy-report.*'
                }}
            }}
        }}
    }}

    post {{
        success {{
            echo 'Pipeline basariyla tamamlandi.'
        }}
        failure {{
            echo 'Pipeline basarisiz oldu!'
        }}
        always {{
            cleanWs()
        }}
    }}
}}
"""
    return pipeline.strip()
