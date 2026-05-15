"""
SARIF 2.1.0 exporter.

SARIF (Static Analysis Results Interchange Format) GitHub Code Scanning
standardıdır. Bu çıktı:
  - GitHub Security tab'ında otomatik gösterilir
  - PR'larda inline annotation açar
  - CodeQL, Semgrep, Snyk gibi araçlarla aynı formatta

Referans: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
"""

from __future__ import annotations

import hashlib
import json

_SARIF_SCHEMA = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/"
    "master/Schemata/sarif-schema-2.1.0.json"
)
_TOOL_VERSION = "1.0.0"


def _severity_to_sarif(severity: str) -> str:
    """DevSecOps AI severity → SARIF level."""
    return {
        "CRITICAL": "error",
        "HIGH":     "error",
        "MEDIUM":   "warning",
        "LOW":      "note",
    }.get(severity.upper(), "warning")


def _build_rules(findings: list[dict]) -> list[dict]:
    """Benzersiz kural tanımları. Her rule_id için bir kez."""
    seen: dict[str, dict] = {}
    for f in findings:
        rule_id = f.get("rule_id") or f.get("vuln_id") or "unknown"
        if rule_id in seen:
            continue
        tags = []
        if f.get("owasp_category"):
            tags.append(f"security/{f['owasp_category']}")
        if f.get("cwe_id"):
            tags.append(f.get("cwe_id"))

        seen[rule_id] = {
            "id": rule_id,
            "name": f.get("issue_name") or rule_id,
            "shortDescription": {
                "text": f.get("message") or f.get("summary") or rule_id
            },
            "fullDescription": {
                "text": f.get("message") or f.get("summary") or rule_id
            },
            "defaultConfiguration": {
                "level": _severity_to_sarif(f.get("severity", "MEDIUM"))
            },
            "properties": {
                "tags": tags,
                "severity": f.get("severity", "MEDIUM"),
                **({"cwe": f["cwe_id"]} if f.get("cwe_id") else {}),
                **({"owasp": f["owasp_category"]} if f.get("owasp_category") else {}),
            },
        }
    return list(seen.values())


def _build_results(findings: list[dict]) -> list[dict]:
    results = []
    for f in findings:
        # False positive olarak işaretlendiyse suppressed göster
        suppressed = f.get("is_false_positive", False)

        rule_id = f.get("rule_id") or f.get("vuln_id") or "unknown"
        file_path = f.get("file", "") or ""
        line = f.get("line") or 1

        result = {
            "ruleId": rule_id,
            "level": _severity_to_sarif(f.get("severity", "MEDIUM")),
            "message": {
                "text": f.get("message") or f.get("summary") or rule_id
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": file_path.lstrip("/"),
                            "uriBaseId": "%SRCROOT%",
                        },
                        "region": {"startLine": int(line) if line else 1},
                    }
                }
            ],
            "properties": {
                "severity": f.get("severity", "MEDIUM"),
                "source":   f.get("source", ""),
                "confidence": f.get("confidence", ""),
                **({"cweId": f["cwe_id"]} if f.get("cwe_id") else {}),
                **({"owaspCategory": f["owasp_category"]} if f.get("owasp_category") else {}),
            },
        }

        if suppressed:
            result["suppressions"] = [
                {
                    "kind": "inSource",
                    "justification": f.get("fp_reason", "LLM false positive filtresi"),
                }
            ]

        results.append(result)
    return results


def to_sarif(
    findings: list[dict],
    repo_url: str = "",
    include_fp: bool = False,
) -> dict:
    """
    Bulgu listesini SARIF 2.1.0 formatına çevirir.

    Args:
        findings:   SAST/SCA/Secret bulgu listesi (FP işaretliler dahil).
        repo_url:   Kaynak repo URL'i (SARIF metadata için).
        include_fp: True → FP bulgular suppressed olarak dahil edilir.
                    False → FP bulgular tamamen dışarıda bırakılır.

    Returns:
        SARIF 2.1.0 dict (JSON'a serialize edilebilir).
    """
    # FP bulgular için karar
    active = [
        f for f in findings
        if include_fp or not f.get("is_false_positive")
    ]

    # SAST bulgularını önce al (SCA/Secret SARIF'ta farklı kolon)
    sast_findings = [f for f in active if f.get("type") == "SAST"]

    return {
        "version": "2.1.0",
        "$schema": _SARIF_SCHEMA,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name":            "DevSecOps AI",
                        "version":         _TOOL_VERSION,
                        "informationUri":  repo_url or "https://github.com",
                        "rules":           _build_rules(sast_findings),
                    }
                },
                "results":   _build_results(sast_findings),
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "toolExecutionNotifications": [],
                    }
                ],
                "properties": {
                    "repoUrl":      repo_url,
                    "totalFindings": len(sast_findings),
                },
            }
        ],
    }


def to_sarif_bytes(findings: list[dict], repo_url: str = "") -> bytes:
    """JSON bytes olarak döner (HTTP response için)."""
    return json.dumps(to_sarif(findings, repo_url), ensure_ascii=False, indent=2).encode("utf-8")
