"""Unit testler — app/security/risk_reporter.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.security.risk_reporter import generate_risk_report


def _sast(findings):
    return {"files_scanned": 5, "findings": findings}

def _sca(findings, packages=10):
    return {"packages_checked": packages, "findings": findings}


def test_empty_returns_100():
    r = generate_risk_report(_sast([]), _sca([]))
    assert r["risk_score"] == 100
    assert r["risk_level"] == "LOW"
    assert r["total_findings"] == 0
    assert r["by_severity"] == {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}


def test_deduction_formula():
    findings = [
        {"type": "SAST", "severity": "CRITICAL", "issue_id": "B601", "file": "a.py", "line": 1, "summary": "x"},
        {"type": "SAST", "severity": "HIGH",     "issue_id": "B608", "file": "b.py", "line": 2, "summary": "y"},
        {"type": "SAST", "severity": "MEDIUM",   "issue_id": "B303", "file": "c.py", "line": 3, "summary": "z"},
        {"type": "SAST", "severity": "LOW",      "issue_id": "B101", "file": "d.py", "line": 4, "summary": "w"},
    ]
    r = generate_risk_report(_sast(findings), _sca([]))
    # 100 - 30(C) - 15(H) - 7(M) - 2(L) = 46
    assert r["risk_score"] == 46
    assert r["risk_level"] == "HIGH"


def test_critical_risk_level():
    findings = [{"type": "SCA", "severity": "CRITICAL", "package": "django", "version": "2.0",
                 "vuln_id": "CVE-x", "summary": "RCE"} for _ in range(3)]
    r = generate_risk_report(_sast([]), _sca(findings))
    # 100 - 3*30 = 10
    assert r["risk_score"] == 10
    assert r["risk_level"] == "CRITICAL"


def test_score_never_negative():
    findings = [{"type": "SAST", "severity": "CRITICAL", "issue_id": "B601",
                 "file": "x.py", "line": 1, "summary": "s"} for _ in range(20)]
    r = generate_risk_report(_sast(findings), _sca([]))
    assert r["risk_score"] == 0


def test_top_findings_max_10():
    findings = [{"type": "SAST", "severity": "LOW", "issue_id": "B101",
                 "file": f"f{i}.py", "line": i, "summary": "s"} for i in range(20)]
    r = generate_risk_report(_sast(findings), _sca([]))
    assert len(r["top_findings"]) == 10
    assert len(r["all_findings"]) == 20


def test_severity_sort_order():
    """Bulgular CRITICAL > HIGH > MEDIUM > LOW sirasiyla gelmeli."""
    findings = [
        {"type": "SAST", "severity": "LOW",      "issue_id": "B101", "file": "a.py", "line": 1, "summary": "s"},
        {"type": "SAST", "severity": "CRITICAL",  "issue_id": "B601", "file": "b.py", "line": 2, "summary": "s"},
        {"type": "SAST", "severity": "MEDIUM",    "issue_id": "B303", "file": "c.py", "line": 3, "summary": "s"},
        {"type": "SAST", "severity": "HIGH",      "issue_id": "B608", "file": "d.py", "line": 4, "summary": "s"},
    ]
    r = generate_risk_report(_sast(findings), _sca([]))
    sevs = [f["severity"] for f in r["all_findings"]]
    assert sevs == ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def test_owasp_mapping():
    findings = [
        {"type": "SAST", "severity": "HIGH", "issue_id": "B608", "file": "a.py", "line": 1, "summary": "SQL injection"},
        {"type": "SAST", "severity": "HIGH", "issue_id": "B303", "file": "b.py", "line": 2, "summary": "MD5"},
    ]
    r = generate_risk_report(_sast(findings), _sca([]))
    owasp_cats = [f.get("owasp", "") for f in r["all_findings"]]
    assert any("Injection" in c for c in owasp_cats)
    assert any("Cryptographic" in c for c in owasp_cats)


def test_sast_sca_combined():
    sast_f = [{"type": "SAST", "severity": "HIGH", "issue_id": "B608", "file": "a.py", "line": 1, "summary": "s"}]
    sca_f  = [{"type": "SCA",  "severity": "CRITICAL", "package": "django", "version": "2.0",
               "vuln_id": "CVE-x", "summary": "RCE"}]
    r = generate_risk_report({"files_scanned": 3, "findings": sast_f},
                             {"packages_checked": 5, "findings": sca_f})
    assert r["total_findings"] == 2
    assert r["sast"]["files_scanned"] == 3
    assert r["sca"]["packages_checked"] == 5
