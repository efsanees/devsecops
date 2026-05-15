"""
LLM tabanlı false positive filtresi.

Sadece HIGH/CRITICAL SAST bulgularına uygulanır (MEDIUM/LOW için FP nadir,
token maliyeti yüksek — atlanır).

Bulgular SILINMEZ; is_false_positive=True ile işaretlenir.
Raporda şeffaf olarak gösterilir, DSOMM skoru hesabına katılmaz.

Kullanım:
    genuine, fp_list = await filter_false_positives(findings, profile)
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

_HIGH_PLUS = {"HIGH", "CRITICAL"}
_MAX_TO_FILTER = 15      # Token limitini aşmamak için
_DEFAULT_THRESHOLD = 0.65


async def filter_false_positives(
    findings: list[dict],
    profile: dict,
    threshold: float = _DEFAULT_THRESHOLD,
) -> tuple[list[dict], list[dict]]:
    """
    Args:
        findings:  SAST bulgu listesi (tüm severity'ler).
        profile:   ProjectProfilerAgent.data (dil/framework için bağlam).
        threshold: Bu güven eşiğinin üzerindeki FP kararları uygulanır.

    Returns:
        (genuine_findings, fp_findings)
        genuine: Gerçek güvenlik sorunu olan bulgular.
        fp_list: Filtrelenen bulgular (is_false_positive=True işaretli).
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        logger.debug("[FPFilter] GROQ_API_KEY yok, filtre atlandı")
        return findings, []

    # Sadece HIGH/CRITICAL SAST bulgular — filtreleme adayları
    candidates_idx = [
        i for i, f in enumerate(findings)
        if f.get("severity", "").upper() in _HIGH_PLUS
        and f.get("type") == "SAST"
    ][:_MAX_TO_FILTER]

    if not candidates_idx:
        return findings, []

    lang = profile.get("language", "bilinmiyor")
    fw   = profile.get("framework", "")
    lang_ctx = f"{lang}" + (f"/{fw}" if fw else "")

    summaries = "\n".join(
        f"[{i}] {findings[idx].get('rule_id','')} | "
        f"{findings[idx].get('file','')}:{findings[idx].get('line','')} | "
        f"{findings[idx].get('message','')[:100]}"
        for i, idx in enumerate(candidates_idx)
    )

    prompt = f"""Sen bir statik analiz uzmanısın. Aşağıdaki SAST bulgularının
gerçek güvenlik sorunu mu yoksa false positive mi olduğunu değerlendir.

Proje: {lang_ctx}

Bulgular:
{summaries}

Her bulgu için JSON formatında yanıt ver:
[
  {{"index": 0, "is_fp": false, "confidence": 0.90, "reason": "..."}},
  ...
]

Kurallar:
- is_fp: true sadece %65+ güvenle false positive olduğuna emin olduğunda
- confidence: 0.0-1.0 arası güven skoru
- reason: tek cümle Türkçe açıklama
- Şüpheli durumda is_fp: false yap (güvenlik adına)
- Sadece JSON array döndür, başka şey yazma"""

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start == -1 or end == 0:
            logger.warning("[FPFilter] JSON array bulunamadı")
            return findings, []

        decisions: list[dict] = json.loads(raw[start:end])
    except Exception as exc:
        logger.warning("[FPFilter] LLM hatası: %s", exc)
        return findings, []

    # Kararları uygula
    fp_indices: set[int] = set()
    for d in decisions:
        local_idx = d.get("index")
        if local_idx is None or local_idx >= len(candidates_idx):
            continue
        global_idx = candidates_idx[local_idx]
        if d.get("is_fp") and (d.get("confidence") or 0) >= threshold:
            findings[global_idx]["is_false_positive"] = True
            findings[global_idx]["fp_confidence"]     = round(d["confidence"], 2)
            findings[global_idx]["fp_reason"]         = d.get("reason", "")
            fp_indices.add(global_idx)

    genuine = [f for i, f in enumerate(findings) if i not in fp_indices]
    fp_list  = [f for i, f in enumerate(findings) if i in fp_indices]

    if fp_list:
        logger.info(
            "[FPFilter] %d/%d HIGH+ bulgu FP olarak filtrelendi (eşik: %.0f%%)",
            len(fp_list), len(candidates_idx), threshold * 100,
        )

    return genuine, fp_list
