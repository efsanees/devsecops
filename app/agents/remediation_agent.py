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

# Bandit kural ID → Türkçe statik düzeltme önerisi.
# Groq yanıt vermezse veya index atlasısa bu tablo devreye girer.
_STATIC_FIXES: dict[str, str] = {
    "B101": "assert ifadesini üretim kodunda kullanmayın; hata kontrolü için if/raise kullanın.",
    "B102": "exec() yerine ast.literal_eval() veya daha güvenli alternatifler kullanın.",
    "B103": "os.chmod() ile dosya izinlerini 0o600 veya daha kısıtlayıcı yapın.",
    "B104": "0.0.0.0 yerine belirli bir IP adresi veya 127.0.0.1 kullanın.",
    "B105": "Şifreleri kod içine gömmek yerine os.environ veya güvenli bir secret manager kullanın.",
    "B106": "Fonksiyon argümanındaki şifreyi os.environ ile çevre değişkeninden alın.",
    "B107": "Varsayılan parametre şifresini kaldırın; şifreyi çevre değişkeninden alın.",
    "B108": "tempfile.mkstemp() veya tempfile.NamedTemporaryFile() kullanın.",
    "B110": "try/except pass bloğu hatayı gizliyor; en azından logging.warning() ekleyin.",
    "B112": "continue boş bir except bloğunda hata gizliyor; loglama ekleyin.",
    "B201": "Flask uygulamasında debug=False yapın veya FLASK_ENV=production kullanın.",
    "B301": "pickle yerine json, msgpack veya güvenli serializasyon kullanın.",
    "B302": "marshal yerine json kullanın.",
    "B303": "MD5/SHA1 yerine hashlib.sha256() veya bcrypt kullanın.",
    "B304": "Zayıf şifreleme yerine AES-256-GCM veya ChaCha20 kullanın.",
    "B305": "ECB modu yerine CBC/GCM modu kullanın.",
    "B306": "mktemp() yerine tempfile.mkstemp() kullanın.",
    "B307": "eval() yerine ast.literal_eval() kullanın; dinamik koddan kaçının.",
    "B308": "mark_safe() yerine Django'nun auto-escaping özelliğine güvenin.",
    "B310": "URL'yi urllib.parse ile doğrulayın; SSRF'ye karşı allowlist uygulayın.",
    "B311": "Kriptografik işlemler için secrets veya os.urandom() kullanın.",
    "B312": "Telnetlib yerine paramiko veya SSH kullanın.",
    "B314": "xml.etree yerine defusedxml kütüphanesini kullanın.",
    "B318": "xml.dom yerine defusedxml kullanın.",
    "B320": "lxml yerine defusedxml kullanın.",
    "B321": "FTP yerine SFTP/SCP kullanın.",
    "B323": "ssl.create_default_context() ile sertifika doğrulamasını etkinleştirin.",
    "B324": "MD5 yerine hashlib.sha256() veya bcrypt.hashpw() kullanın.",
    "B401": "telnetlib yerine paramiko (SSH) kullanın.",
    "B402": "ftplib yerine ftplib.FTP_TLS veya SFTP kullanın.",
    "B403": "pickle yerine json veya güvenli serializasyon kullanın.",
    "B404": "subprocess.run() ile shell=False ve komutları liste olarak geçirin.",
    "B405": "xml.etree yerine defusedxml kullanın.",
    "B501": "verify=True yapın; özel CA için verify='/path/to/ca-bundle.crt' kullanın.",
    "B502": "ssl.PROTOCOL_TLS_CLIENT ile minimum TLS 1.2 zorunlu kılın.",
    "B503": "Güvenli cipher suite listesi: ssl.create_default_context() kullanın.",
    "B504": "ssl.PROTOCOL_TLS_CLIENT kullanın; eski protokolleri devre dışı bırakın.",
    "B505": "RSA için minimum 2048 bit, EC için minimum 256 bit anahtar kullanın.",
    "B506": "yaml.safe_load() kullanın; yaml.load() asla kullanmayın.",
    "B601": "Paramiko shell komutlarını sanitize edin; shlex.quote() ile güvenceye alın.",
    "B602": "subprocess.run(['cmd', arg1], shell=False) formatına geçin.",
    "B603": "subprocess.run() çağrısında shell=False kullanın ve komutları liste olarak geçirin.",
    "B604": "Shell fonksiyon çağrılarından kaçının; subprocess.run() listesi kullanın.",
    "B605": "os.system() yerine subprocess.run(['cmd', arg1], shell=False) kullanın.",
    "B606": "os.popen() yerine subprocess.run() kullanın.",
    "B607": "Tam yürütülebilir dosya yolu kullanın: /usr/bin/cmd gibi.",
    "B608": "Parametreli sorgu kullanın: cursor.execute('SELECT * FROM t WHERE id=%s', (id,))",
    "B609": "Wildcard yerine açık dosya listesi kullanın; shlex.quote() uygulayın.",
    "B610": "Django ORM filter() kullanın; extra() ve RawSQL() yerine.",
    "B611": "Django ORM filter() kullanın; RawSQL() yerine.",
    "B701": "Jinja2'de autoescape=True yapın: Environment(autoescape=True).",
    "B702": "Mako template yerine Jinja2 veya Django şablonları kullanın.",
    "B703": "mark_safe() yerine Django auto-escaping kullanın; zorunluysa format_html().",
    # Semgrep kuralları
    "PYTHON.LANG.SECURITY.AUDIT.MD5-USED-AS-PASSWORD.MD5-USED-AS-PASSWORD":
        "hashlib.md5() yerine hashlib.sha256() veya bcrypt.hashpw() kullanın.",
    "PYTHON.LANG.SECURITY.AUDIT.FORMATTED-SQL-QUERY.FORMATTED-SQL-QUERY":
        "Parametreli sorgu kullanın: cursor.execute('SELECT * FROM t WHERE id=%s', (id,))",
    "PYTHON.LANG.SECURITY.AUDIT.SUBPROCESS-SHELL-TRUE.SUBPROCESS-SHELL-TRUE":
        "subprocess.run() çağrısında shell=False kullanın, komutları liste olarak geçirin.",
    "PYTHON.LANG.SECURITY.AUDIT.OS-SYSTEM-INJECTION.OS-SYSTEM-INJECTION":
        "os.system() yerine subprocess.run(['cmd', arg1], shell=False) kullanın.",
    "PYTHON.DJANGO.SECURITY.INJECTION.TAINTED-SQL-STRING.TAINTED-SQL-STRING":
        "Django ORM filter() kullanın; string birleştirmeli SQL sorgularından kaçının.",
    "PYTHON.FLASK.SECURITY.AUDIT.HARDCODED-SECRET.HARDCODED-SECRET":
        "SECRET_KEY değerini os.environ['SECRET_KEY'] ile çevre değişkeninden alın.",
    "PYTHON.LANG.SECURITY.AUDIT.HARDCODED-PASSWORD.HARDCODED-PASSWORD":
        "Şifreleri kod içine gömmek yerine os.environ veya güvenli bir vault kullanın.",
    "PYTHON.REQUESTS.BEST-PRACTICE.USE-TIMEOUT.USE-TIMEOUT":
        "requests çağrısına timeout ekleyin: requests.get(url, timeout=10)",
    "PYTHON.LANG.SECURITY.AUDIT.EVAL-INJECTION.EVAL-INJECTION":
        "eval() yerine ast.literal_eval() kullanın.",
}


def _apply_static_fixes(findings: list[dict]) -> None:
    """
    Groq'tan fix_suggestion almayan bulgulara statik tablo üzerinden öneri ekler.
    Sadece eksik olanları tamamlar — Groq'un ürettiklerinin üzerine yazmaz.
    Hem Bandit (B105) hem Semgrep (python.lang.security.*) rule ID'leri destekler.
    """
    for f in findings:
        if f.get("fix_suggestion"):
            continue
        rule_id = (f.get("rule_id") or f.get("issue_id") or "").upper()
        static = _STATIC_FIXES.get(rule_id)
        if static:
            f["fix_suggestion"] = static


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

    # Severity sırasına göre sırala — HIGH önce, hepsine öneri üret
    _SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_findings = sorted(
        sast_findings + sca_findings,
        key=lambda f: _SEV_ORDER.get(f.get("severity", "").upper(), 4),
    )
    candidates = all_findings[:_MAX_FINDINGS]

    if not candidates:
        logger.debug("[Remediation] Bulgu yok, atlandı")
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

        logger.info("[Remediation] %d/%d bulguya LLM düzeltme önerisi eklendi", applied, len(candidates))

    except json.JSONDecodeError as exc:
        logger.warning("[Remediation] JSON parse hatası: %s", exc)
    except Exception as exc:
        logger.warning("[Remediation] Groq hatası: %s", exc)

    # Groq'tan öneri alamayan TÜM SAST bulgularına statik tablo fallback uygula.
    # Candidates dışında kalan LOW bulgular da kapsanır (SCA dolunca dışarıda kalabiliyorlar).
    _apply_static_fixes(sast_findings)
    _apply_static_fixes(sca_findings)

    all_with_fix = sum(1 for f in (sast_findings + sca_findings) if f.get("fix_suggestion"))
    logger.info("[Remediation] Toplam: %d/%d bulguda düzeltme önerisi var",
                all_with_fix, len(sast_findings) + len(sca_findings))
