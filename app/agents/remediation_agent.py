"""
Remediation Agent — HIGH/CRITICAL bulgular için Groq LLM'e somut düzeltme önerisi ister.

Yaklaşım:
  - SAST ve SCA findings listesinden severity=HIGH veya CRITICAL olanları al (max 10)
  - Tek Groq API çağrısıyla JSON formatında düzeltme önerileri al
  - Her bulguya in-place olarak fix_suggestion alanı ekle
  - GROQ_API_KEY yoksa veya hata oluşursa sessizce devam et
"""

import json
import logging
import os

from groq import Groq

logger = logging.getLogger(__name__)

_HIGH_OR_CRITICAL = {"HIGH", "CRITICAL"}
_MAX_FINDINGS = 10


def _summarize(f: dict, idx: int) -> str:
    ftype = f.get("type", "")
    sev = f.get("severity", "")
    if ftype == "SAST":
        loc = f"{f.get('file', '')}:{f.get('line', '')}" if f.get("file") else ""
        return (
            f"[{idx}] SAST | {sev} | {f.get('rule_id', '')} | {loc} | "
            f"{f.get('message', '')[:120]} | CWE: {f.get('cwe_id', '?')}"
        )
    if ftype == "SCA":
        return (
            f"[{idx}] SCA | {sev} | {f.get('vuln_id', '')} | "
            f"paket: {f.get('package', '')}@{f.get('version', '')} | "
            f"{f.get('summary', '')[:120]} | sabit sürüm: {f.get('fixed_in', '?')}"
        )
    return f"[{idx}] {ftype} | {sev} | {f.get('message', f.get('title', ''))[:120]}"


async def run_remediation(
    sast_findings: list[dict],
    sca_findings: list[dict],
    profile: dict,
) -> None:
    """
    HIGH/CRITICAL bulgulara in-place olarak fix_suggestion alanı ekler.
    Başarısız olursa hiçbir şey değişmez.
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        logger.debug("[Remediation] GROQ_API_KEY yok, atlandı")
        return

    candidates = [
        f for f in (sast_findings + sca_findings)
        if f.get("severity", "").upper() in _HIGH_OR_CRITICAL
    ][:_MAX_FINDINGS]

    if not candidates:
        logger.debug("[Remediation] HIGH/CRITICAL bulgu yok, atlandı")
        return

    lang = profile.get("language", "bilinmiyor")
    framework = profile.get("framework", "")
    lang_ctx = f"{lang}{f' / {framework}' if framework else ''}"

    summaries = "\n".join(_summarize(f, i) for i, f in enumerate(candidates))

    prompt = f"""Sen bir kıdemli DevSecOps güvenlik mühendisisin.
Aşağıdaki güvenlik bulgularının her biri için kısa, teknik ve uygulanabilir Türkçe düzeltme önerisi ver.

Proje dili/çerçevesi: {lang_ctx}

Bulgular:
{summaries}

Yanıt formatı — sadece JSON array, başka hiçbir şey yazma:
[
  {{"index": 0, "fix": "...somut tek-cümle düzeltme adımı..."}},
  {{"index": 1, "fix": "..."}},
  ...
]

Kurallar:
- Her fix en fazla 2 kısa cümle
- Somut ol: paket adı, versiyon, fonksiyon adı, parametre gibi detaylar ver
- Örnek: "requests>=2.32.0 sürümüne yükseltin." veya "subprocess.run() çağrısında shell=False kullanın."
- Sadece JSON array döndür"""

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()

        # LLM bazen JSON öncesine açıklama ekler; sadece [...] kısmını al
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            logger.warning("[Remediation] JSON array bulunamadı, yanıt: %s", raw[:200])
            return

        fixes: list[dict] = json.loads(raw[start:end])

        applied = 0
        for item in fixes:
            idx = item.get("index")
            fix = (item.get("fix") or "").strip()
            if fix and idx is not None and 0 <= idx < len(candidates):
                candidates[idx]["fix_suggestion"] = fix
                applied += 1

        logger.info("[Remediation] %d/%d bulguya düzeltme önerisi eklendi", applied, len(candidates))

    except json.JSONDecodeError as exc:
        logger.warning("[Remediation] JSON parse hatası: %s", exc)
    except Exception as exc:
        logger.warning("[Remediation] Groq hatası: %s", exc)
