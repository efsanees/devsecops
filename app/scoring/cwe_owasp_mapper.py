"""
CWE / OWASP Top 10 (2021) haritalama.

Kullanım:
    from app.scoring.cwe_owasp_mapper import enrich_finding
    finding = enrich_finding(finding)
    # → finding["cwe_id"] = "CWE-89"
    # → finding["owasp_category"] = "A03:2021"
"""

# Bandit kural ID → CWE ID
BANDIT_TO_CWE: dict[str, str] = {
    "B101": "CWE-617",  # reachable assertion
    "B102": "CWE-78",   # exec
    "B103": "CWE-732",  # dosya izinleri
    "B104": "CWE-605",  # bağlama 0.0.0.0
    "B105": "CWE-259",  # hardcoded password literal
    "B106": "CWE-259",  # hardcoded password fonksiyon arg
    "B107": "CWE-259",  # hardcoded password default
    "B108": "CWE-377",  # geçici dosya
    "B201": "CWE-94",   # Flask debug=True
    "B301": "CWE-502",  # pickle
    "B302": "CWE-502",  # marshal
    "B303": "CWE-327",  # MD5/SHA1
    "B304": "CWE-327",  # zayıf şifreleme
    "B305": "CWE-327",  # zayıf şifreleme modu
    "B306": "CWE-377",  # mktemp
    "B307": "CWE-78",   # eval
    "B308": "CWE-79",   # mark_safe
    "B310": "CWE-918",  # urllib open
    "B311": "CWE-338",  # random (non-crypto)
    "B312": "CWE-319",  # telnetlib
    "B314": "CWE-611",  # XML ElementTree
    "B318": "CWE-611",  # XML DOM
    "B320": "CWE-611",  # lxml
    "B321": "CWE-319",  # FTP
    "B322": "CWE-78",   # input (Python 2)
    "B323": "CWE-295",  # unverified context
    "B324": "CWE-327",  # hashlib zayıf
    "B401": "CWE-319",  # import telnetlib
    "B402": "CWE-319",  # import ftplib
    "B403": "CWE-502",  # import pickle
    "B404": "CWE-78",   # import subprocess
    "B405": "CWE-611",  # import xml.etree
    "B501": "CWE-295",  # SSL verify=False
    "B502": "CWE-326",  # SSL eski versiyon
    "B503": "CWE-326",  # SSL zayıf cipher
    "B504": "CWE-326",  # SSL eski protokol
    "B505": "CWE-326",  # zayıf kriptografik anahtar
    "B506": "CWE-20",   # yaml.load unsafe
    "B601": "CWE-78",   # paramiko shell
    "B602": "CWE-78",   # subprocess shell=True
    "B603": "CWE-78",   # subprocess
    "B604": "CWE-78",   # shell fonksiyon
    "B605": "CWE-78",   # os.system
    "B606": "CWE-78",   # os.popen
    "B607": "CWE-78",   # partial executable
    "B608": "CWE-89",   # SQL injection
    "B609": "CWE-78",   # wildcard injection
    "B610": "CWE-89",   # Django extra
    "B611": "CWE-89",   # Django RawSQL
    "B701": "CWE-94",   # jinja2 autoescape
    "B702": "CWE-94",   # mako
    "B703": "CWE-79",   # Django mark_safe
}

# CWE ID → OWASP Top 10 (2021) kategorisi
CWE_TO_OWASP: dict[str, str] = {
    # A01: Broken Access Control
    "CWE-22":  "A01:2021",
    "CWE-23":  "A01:2021",
    "CWE-59":  "A01:2021",
    "CWE-200": "A01:2021",
    "CWE-201": "A01:2021",
    "CWE-264": "A01:2021",
    "CWE-275": "A01:2021",
    "CWE-276": "A01:2021",
    "CWE-284": "A01:2021",
    "CWE-285": "A01:2021",
    "CWE-352": "A01:2021",
    "CWE-359": "A01:2021",
    "CWE-377": "A01:2021",
    "CWE-425": "A01:2021",
    "CWE-497": "A01:2021",
    "CWE-538": "A01:2021",
    "CWE-540": "A01:2021",
    "CWE-548": "A01:2021",
    "CWE-552": "A01:2021",
    "CWE-566": "A01:2021",
    "CWE-601": "A01:2021",
    "CWE-605": "A01:2021",
    "CWE-732": "A01:2021",
    # A02: Cryptographic Failures
    "CWE-295": "A02:2021",
    "CWE-310": "A02:2021",
    "CWE-319": "A02:2021",
    "CWE-321": "A02:2021",
    "CWE-326": "A02:2021",
    "CWE-327": "A02:2021",
    "CWE-328": "A02:2021",
    "CWE-330": "A02:2021",
    "CWE-331": "A02:2021",
    "CWE-335": "A02:2021",
    "CWE-338": "A02:2021",
    "CWE-340": "A02:2021",
    "CWE-347": "A02:2021",
    # A03: Injection
    "CWE-20":  "A03:2021",
    "CWE-74":  "A03:2021",
    "CWE-77":  "A03:2021",
    "CWE-78":  "A03:2021",
    "CWE-79":  "A03:2021",
    "CWE-80":  "A03:2021",
    "CWE-83":  "A03:2021",
    "CWE-88":  "A03:2021",
    "CWE-89":  "A03:2021",
    "CWE-90":  "A03:2021",
    "CWE-91":  "A03:2021",
    "CWE-94":  "A03:2021",
    "CWE-95":  "A03:2021",
    "CWE-98":  "A03:2021",
    "CWE-116": "A03:2021",
    "CWE-138": "A03:2021",
    "CWE-184": "A03:2021",
    "CWE-470": "A03:2021",
    "CWE-564": "A03:2021",
    "CWE-610": "A03:2021",
    "CWE-611": "A03:2021",
    "CWE-917": "A03:2021",
    # A04: Insecure Design
    "CWE-73":  "A04:2021",
    "CWE-183": "A04:2021",
    "CWE-209": "A04:2021",
    "CWE-256": "A04:2021",
    "CWE-269": "A04:2021",
    "CWE-311": "A04:2021",
    "CWE-312": "A04:2021",
    "CWE-313": "A04:2021",
    "CWE-316": "A04:2021",
    "CWE-434": "A04:2021",
    "CWE-444": "A04:2021",
    "CWE-501": "A04:2021",
    "CWE-522": "A04:2021",
    "CWE-539": "A04:2021",
    "CWE-598": "A04:2021",
    "CWE-602": "A04:2021",
    "CWE-642": "A04:2021",
    "CWE-656": "A04:2021",
    # A05: Security Misconfiguration
    "CWE-2":   "A05:2021",
    "CWE-11":  "A05:2021",
    "CWE-16":  "A05:2021",
    "CWE-260": "A05:2021",
    "CWE-315": "A05:2021",
    "CWE-520": "A05:2021",
    "CWE-526": "A05:2021",
    "CWE-537": "A05:2021",
    "CWE-541": "A05:2021",
    "CWE-547": "A05:2021",
    "CWE-614": "A05:2021",
    "CWE-617": "A05:2021",
    "CWE-749": "A05:2021",
    "CWE-942": "A05:2021",
    # A06: Vulnerable and Outdated Components
    "CWE-937":  "A06:2021",
    "CWE-1035": "A06:2021",
    "CWE-1104": "A06:2021",
    # A07: Identification and Authentication Failures
    "CWE-255": "A07:2021",
    "CWE-259": "A07:2021",
    "CWE-287": "A07:2021",
    "CWE-288": "A07:2021",
    "CWE-290": "A07:2021",
    "CWE-294": "A07:2021",
    "CWE-297": "A07:2021",
    "CWE-302": "A07:2021",
    "CWE-304": "A07:2021",
    "CWE-306": "A07:2021",
    "CWE-307": "A07:2021",
    "CWE-346": "A07:2021",
    "CWE-384": "A07:2021",
    "CWE-521": "A07:2021",
    "CWE-523": "A07:2021",
    "CWE-620": "A07:2021",
    "CWE-640": "A07:2021",
    "CWE-798": "A07:2021",
    # A08: Software and Data Integrity Failures
    "CWE-345": "A08:2021",
    "CWE-353": "A08:2021",
    "CWE-426": "A08:2021",
    "CWE-494": "A08:2021",
    "CWE-502": "A08:2021",
    "CWE-565": "A08:2021",
    "CWE-784": "A08:2021",
    "CWE-829": "A08:2021",
    # A09: Security Logging and Monitoring Failures
    "CWE-117": "A09:2021",
    "CWE-223": "A09:2021",
    "CWE-532": "A09:2021",
    "CWE-778": "A09:2021",
    # A10: Server-Side Request Forgery
    "CWE-918": "A10:2021",
}

# Görüntü etiketleri
OWASP_LABELS: dict[str, str] = {
    "A01:2021": "A01 Broken Access Control",
    "A02:2021": "A02 Cryptographic Failures",
    "A03:2021": "A03 Injection",
    "A04:2021": "A04 Insecure Design",
    "A05:2021": "A05 Security Misconfiguration",
    "A06:2021": "A06 Vulnerable Components",
    "A07:2021": "A07 Auth Failures",
    "A08:2021": "A08 Software & Data Integrity",
    "A09:2021": "A09 Logging & Monitoring",
    "A10:2021": "A10 SSRF",
}


def enrich_finding(finding: dict) -> dict:
    """
    finding sözlüğüne cwe_id ve owasp_category ekler/günceller.

    - SAST Bandit: rule_id'den BANDIT_TO_CWE ile CWE bulur.
    - SAST Semgrep: metadata_cwe alanından (semgrep_runner tarafından set edilir) CWE alır.
    - SCA: cwe_id yoksa varsayılan A06:2021 atar.
    - owasp_category zaten varsa korur; yoksa CWE_TO_OWASP'tan bulur.
    """
    finding = dict(finding)

    cwe_id = finding.get("cwe_id")

    if not cwe_id:
        rule_id = (finding.get("rule_id") or "").upper()
        # Bandit kuralları B ile başlar
        if rule_id.startswith("B") and len(rule_id) >= 3:
            cwe_id = BANDIT_TO_CWE.get(rule_id)

        # Semgrep metadata CWE alanı (semgrep_runner tarafından set edilir)
        if not cwe_id:
            raw_cwe = finding.get("metadata_cwe")
            if raw_cwe:
                if isinstance(raw_cwe, list):
                    raw_cwe = raw_cwe[0] if raw_cwe else None
                if raw_cwe:
                    cwe_id = str(raw_cwe).strip()
                    if cwe_id and not cwe_id.upper().startswith("CWE-"):
                        cwe_id = f"CWE-{cwe_id}"

    finding["cwe_id"] = cwe_id

    # OWASP kategori
    owasp = finding.get("owasp_category")
    if not owasp and cwe_id:
        owasp = CWE_TO_OWASP.get(cwe_id.upper())
    if not owasp and finding.get("type") == "SCA":
        owasp = "A06:2021"

    finding["owasp_category"] = owasp or None
    return finding
