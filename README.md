# DevSecOps AI — Akıllı Pipeline Asistanı

GitHub reponuzu analiz eden, güvenlik açıklarını tespit eden ve projeye özel bir CI/CD pipeline üreten multi-agent web uygulaması.

## Özellikler

- **Multi-agent analiz** — 5 bağımsız agent paralel çalışır (asyncio.gather)
- **SAST** — Bandit (Python) + Semgrep (çok dilli, Docker)
- **SCA** — OSV.dev Batch API + Trivy filesystem (CVE dedupe)
- **Secret tarama** — Gitleaks (Docker, maskeli çıktı)
- **Pipeline analizi** — GitHub Actions / GitLab CI / Jenkins / Azure DevOps
- **DSOMM skoru** — 5 kategori, 0-100, Başlangıç/Gelişen/Olgun seviyesi
- **LLM yorumu** — Groq (Llama-3.3-70b) ile öncelikli eylem önerileri
- **CI/CD üretimi** — Projeye özel GitHub Actions / GitLab CI / Jenkins YAML
- **Rapor export** — Markdown + PDF (WeasyPrint)
- **Real-time progress** — WebSocket ile agent ilerleme takibi

## Hızlı Başlangıç

### Docker Compose (Önerilen)

```bash
cp .env.example .env
# .env dosyasına GROQ_API_KEY değerini gir
docker-compose up --build
```

Uygulama açılıyor: `http://localhost`

### Manuel Kurulum

**Backend:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # GROQ_API_KEY doldur
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Uygulama: `http://localhost:5173`

### Gereksinimler

| Araç | Sürüm | Zorunlu |
|---|---|---|
| Python | 3.11+ | Evet |
| Node.js | 18+ | Evet |
| Docker Desktop | Herhangi | Opsiyonel* |
| Groq API Key | — | Evet |

*Docker olmadan Semgrep, Trivy ve Gitleaks çalışmaz; Bandit + OSV.dev ile devam eder.

## Kullanım

1. `http://localhost`'u açın
2. GitHub repo URL'sini girin (ör. `https://github.com/OWASP/NodeGoat`)
3. **Tam Analiz** modunu seçin
4. 5 agent'ın paralel çalışmasını izleyin
5. DSOMM skoru, bulgular, LLM önerileri ve pipeline YAML'ı inceleyin
6. Markdown veya PDF raporu indirin

## Mimari

```
Frontend (React + Vite + Tailwind)
    │ HTTP / WebSocket
    ▼
FastAPI Backend
    │
    ├── POST /job → BackgroundTasks → Orchestrator.run()
    │
    └── Orchestrator (asyncio.gather)
            │
            ├── [1] ProjectProfilerAgent  (sequential)
            │         analyze_repo() → dil, framework, file_list
            │
            ├── [2] SASTAgent             ┐
            ├── [3] SCAAgent              ├── paralel (asyncio.gather)
            ├── [4] SecretAgent           │
            └── [5] PipelineAnalyzerAgent ┘
                      │
                      ▼
              LLM Reasoner (Groq) → risk özeti
              Pipeline Generator  → YAML
              DSOMM Scorer        → 0-100 puan
              DB kaydet (SQLite)
              WebSocket → job_completed
```

Detaylı mimari için [ARCHITECTURE.md](ARCHITECTURE.md) dosyasına bakın.

## Teknoloji Yığını

**Backend**
- FastAPI + uvicorn (async API)
- SQLAlchemy + SQLite (job ve rapor saklama)
- Groq SDK — Llama-3.3-70b (LLM)
- Jinja2 + WeasyPrint (rapor export)
- slowapi (rate limiting)

**Güvenlik Araçları**
- Bandit — Python SAST (subprocess)
- Semgrep — çok dilli SAST (Docker)
- OSV.dev Batch API — bağımlılık CVE
- Trivy — kapsamlı SCA + IaC (Docker)
- Gitleaks — secret tarama (Docker)

**Frontend**
- React 18 + Vite
- Tailwind CSS
- React Router v6
- highlight.js (YAML syntax)

## API Dokümantasyonu

Sunucu çalışırken: `http://localhost:8000/docs`

Temel endpoint'ler:

| Endpoint | Açıklama |
|---|---|
| `POST /job` | Multi-agent analiz başlat (202) |
| `GET /job/{id}` | Job durumu ve sonucu |
| `WS /ws/{id}` | Gerçek zamanlı progress |
| `GET /job/{id}/yaml` | Pipeline YAML indir |
| `GET /job/{id}/report.md` | Markdown rapor |
| `GET /job/{id}/report.pdf` | PDF rapor |

## Desteklenen Diller

Python, Node.js, Java (Maven/Gradle), Go, Rust, .NET, PHP, Ruby

## Desteklenen CI/CD Platformları

GitHub Actions, GitLab CI, Jenkins, Azure DevOps, Bitbucket

## Lisans

MIT
