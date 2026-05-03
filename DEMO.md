# Demo Senaryosu — Bitirme Sunumu

## Demo Öncesi Kontrol Listesi

- [ ] Docker Desktop açık ve çalışıyor (`docker info` ile doğrula)
- [ ] `.env` dosyasında `GROQ_API_KEY` dolu
- [ ] `uvicorn main:app --reload` backend çalışıyor (port 8000)
- [ ] `npm run dev` frontend çalışıyor (port 5173)
- [ ] Browser'da `http://localhost:5173` açık
- [ ] İnternet bağlantısı var (GitHub API + Groq + OSV.dev)
- [ ] Yedek ekran görüntüleri hazır (internet yoksa)

## Demo Repoları

| Repo | Dil | Neden iyi demo? |
|---|---|---|
| `https://github.com/OWASP/NodeGoat` | Node.js | Kasıtlı zafiyetler, düşük skor |
| `https://github.com/WebGoat/WebGoat` | Java | Çok sayıda CVE, CI/CD eksik |
| `https://github.com/pallets/flask` | Python | Temiz repo, yüksek skor karşılaştırması |

**Önerilen:** NodeGoat ile başla (düşük skor = çarpıcı demo), sonra Flask ile karşılaştır.

---

## Sunum Akışı (~7 dakika)

### 0:00 – 0:45 | Giriş

> "Bu proje, geliştiricilerin güvenlik konusunda uzman olmadan da güvenli yazılım geliştirmesine yardımcı olmak için tasarlanmış bir DevSecOps asistanıdır. Kullanıcı bir GitHub repo URL'si giriyor, sistem 5 agent'ı paralel olarak çalıştırıyor ve sonunda hem kapsamlı bir güvenlik raporu hem de projeye özel bir CI/CD pipeline üretiyor."

### 0:45 – 1:30 | Mimari açıklaması (ARCHITECTURE.md'den)

> "Sistemin kalbinde bir Orchestrator var. İlk olarak ProjectProfilerAgent çalışıyor ve reponun dilini, framework'ünü tespit ediyor. Bu bilgi hazırlandıktan sonra 4 agent eş zamanlı başlıyor — asyncio.gather ile gerçek anlamda paralel. Biri statik kod analizi (Bandit + Semgrep), biri bağımlılık güvenliği (OSV.dev + Trivy), biri hardcoded secret taraması (Gitleaks), biri de mevcut CI/CD pipeline'ı analiz ediyor."

Mermaid diyagramını ekranda göster.

### 1:30 – 4:30 | Canlı Demo

1. Browser'da `http://localhost:5173` aç
2. URL gir: `https://github.com/OWASP/NodeGoat`
3. **Tam Analiz** modunu seç, GitHub Actions platformunu seç
4. "Tam Analiz Başlat" tıkla

> "Sistem şu an 5 agent'ı paralel çalıştırıyor. Sol tarafta gerçek zamanlı olarak hangi agent'ın çalıştığını, hangisinin tamamlandığını görebiliyoruz."

5. Agent'lar tamamlandıkça kartlar yeşile dönüyor

> "Pipeline Analyzer'ın 'Tamamlandı' olduğunu gördünüz — NodeGoat'ta hiç CI/CD dosyası yok, bu da zaten büyük bir risk işareti."

6. Rapor sayfasına geçince:

**DSOMM skoru göster:**
> "Sistem DSOMM — DevSecOps Maturity Model — standardına göre 5 kategoride değerlendiriyor. NodeGoat 23/100 alıyor, Başlangıç seviyesinde. Implementation kategorisi çok düşük çünkü yüksek kritiklik seviyesinde çok sayıda bulgu var."

**Bulgular tablosunu göster:**
> "SAST sekmesinde Semgrep'in bulduğu SQL injection ve eval kullanımı örnekleri görünüyor. SCA sekmesinde eski versiyon bağımlılıkların CVE'leri listeleniyor. Secret sekmesinde hardcoded MongoDB bağlantı URI'si var — değer maskeli gösteriliyor, asla tam değer saklanmıyor."

**LLM yorumunu göster:**
> "AI bu bulguları yorumluyor ve öncelikli 3 eylemi öneriyor. Bu satırlar Groq üzerindeki Llama modeli tarafından üretildi, şablon değil."

**Pipeline YAML göster:**
> "Ve işte üretilen GitHub Actions pipeline. Projenin Node.js olduğunu tespit etti, npm install ve test adımlarını ekledi, Trivy güvenlik taramasını dahil etti. Bunu .github/workflows/ altına kopyalayıp direkt kullanabilirsiniz."

### 4:30 – 5:30 | Rapor indirme

7. "Markdown Rapor" butonuna tıkla, dosyayı aç

> "Analiz sonuçları Markdown ve PDF formatında indirilebilir. Tüm bulgular, DSOMM skoru ve pipeline YAML tek dokümanda."

### 5:30 – 6:30 | API dokümantasyonu

8. `http://localhost:8000/docs` aç

> "Backend FastAPI ile yazıldığı için otomatik OpenAPI dokümantasyonu var. POST /job yeni multi-agent akışını başlatıyor, WebSocket /ws/{job_id} gerçek zamanlı event'leri iletıyor."

### 6:30 – 7:00 | Kapanış

> "14 günlük geliştirme sürecinde 5 agent, 3 Docker tabanlı güvenlik aracı, DSOMM tabanlı skorlama ve LLM destekli öneri sistemi kuruldu. Sistem standalone çalışıyor — mevcut repo'nuza hiçbir değişiklik yapmadan dışarıdan analiz edebiliyorsunuz."

---

## Jüri Soruları ve Cevaplar

**S: "Neden LangGraph veya CrewAI kullanmadın?"**
> "Bu kullanım senaryosu için custom asyncio orchestrator daha uygun. Agent'larımız deterministik görevler yapıyor — LangGraph veya CrewAI'nin sohbet tabanlı yapısına ihtiyacımız yok. `asyncio.gather` ile daha az bağımlılıkla aynı paralelizmi elde ettik ve debug çok daha kolay."

**S: "Docker olmadan çalışıyor mu?"**
> "Evet. Docker yoksa Semgrep, Trivy ve Gitleaks atlanıyor, sistem Bandit (Python SAST) ve OSV.dev (SCA) ile devam ediyor. Bu durum agent result'ında `skipped_reason` olarak raporlanıyor."

**S: "Büyük repolar ne kadar sürer?"**
> "Test ettiğimiz ortalama repolar (~200 dosya) 60-90 saniye sürüyor. En uzun süren Semgrep — `--config=auto` tüm dili tarıyor. Trivy DB cache'lendiği için ilk çalışmadan sonra çok daha hızlı."

**S: "Güvenlik bulguları false positive içermez mi?"**
> "İçerebilir, özellikle Semgrep `--config=auto` bazen aşırı agresif. Üretim kullanımında `.semgrepignore` veya özel kural seti ile ayarlanabilir. Şu anki yapı 'broad scan, kullanıcı filtreler' yaklaşımı."

**S: "Hardcoded secret'ları neden tam göstermiyorsun?"**
> "Güvenlik pratiği. Gitleaks `--redact` flag ile çalışıyor, biz de ek katman olarak `AKIA...MPLE` formatında maskeliyoruz. Rapor dosyası okunur okunmaz diskten siliniyor."

**S: "DSOMM nedir?"**
> "DevSecOps Maturity Model — OWASP'ın DevSecOps olgunluğunu ölçmek için tanımladığı framework. Biz basitleştirilmiş 5 kategori versiyonunu kullandık: Build/Deployment, Test, Implementation, Bilgi Toplama, Kültür. Toplam 100 puan, üç seviye."

**S: "Veriler nerede saklanıyor?"**
> "SQLite veritabanında. Job ID, durum, agent sonuçları ve nihai rapor JSON olarak saklanıyor. Docker Compose'da named volume kullanılıyor, container silinse de veriler korunuyor."

---

## Yedek Plan (İnternet Yoksa)

1. Önceden tamamlanmış bir analiz sonucunu local state olarak kaydet
2. Browser'ı F5 yenileme yerine kaydedilmiş JSON ile `/result` sayfasını direkt aç:
   ```javascript
   // Browser console'da:
   history.pushState({type:'job', data: SAVED_RESULT}, '', '/result')
   location.reload()
   ```
3. PDF raporu zaten indirilmiş olarak göster
4. API dokümantasyonu (`/docs`) internet gerektirmez

---

## Slayt İçeriği (5-8 slayt)

1. **Kapak** — "DevSecOps AI: Akıllı Pipeline Asistanı"
2. **Problem** — Güvenli yazılım geliştirmek uzmanlık gerektirir, CI/CD kurulumu zaman alır
3. **Çözüm** — Multi-agent sistem: analiz + tarama + üretim + skorlama
4. **Mimari** — Component diyagramı (ARCHITECTURE.md'den kopyala)
5. **Teknoloji** — FastAPI, asyncio, Groq, Bandit, Semgrep, Trivy, Gitleaks, DSOMM
6. **Demo** — Ekran görüntüleri: progress sayfası + DSOMM dashboard + findings
7. **Sonuçlar** — NodeGoat vs Flask skor karşılaştırması, üretilen YAML örneği
8. **Gelecek** — Daha fazla dil, GitHub App entegrasyonu, custom DSOMM profilleri
