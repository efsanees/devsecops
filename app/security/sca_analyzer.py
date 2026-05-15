"""
SCA (Software Composition Analysis) Analyzer — OSV.dev Batch API

Desteklenen ekosistemler:
  - PyPI       : requirements.txt
  - npm        : package.json
  - NuGet      : *.csproj
  - Maven      : pom.xml
  - Go         : go.mod
  - crates.io  : Cargo.lock
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Callable

import requests

logger = logging.getLogger(__name__)

OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_TIMEOUT = 20


# ---------------------------------------------------------------------------
# Parser'lar
# ---------------------------------------------------------------------------

def _parse_requirements(content: str) -> list[dict]:
    """PyPI — requirements.txt"""
    packages: list[dict] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-", "git+", "http")):
            continue
        m = re.match(r"^([a-zA-Z0-9_.\-]+(?:\[[^\]]+\])?)\s*(?:[><=!~]+\s*([^\s,;]+))?", line)
        if m:
            # Strip extras like [all] from package name — OSV uses bare names
            name = re.sub(r"\[.*?\]", "", m.group(1)).strip()
            packages.append({
                "name": name,
                "version": (m.group(2) or "").strip().lstrip("="),
            })
    return packages


def _parse_package_json(content: str) -> list[dict]:
    """npm — package.json"""
    packages: list[dict] = []
    try:
        pkg = json.loads(content)
        all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        for name, ver in all_deps.items():
            packages.append({
                "name": name,
                "version": re.sub(r"[^0-9.]", "", str(ver)).strip("."),
            })
    except Exception as exc:
        logger.error(f"package.json parse hatası: {exc}")
    return packages


def _parse_csproj(content: str) -> list[dict]:
    """NuGet — *.csproj"""
    packages: list[dict] = []
    try:
        root = ET.fromstring(content)
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "PackageReference":
                name = elem.get("Include") or elem.get("include", "")
                version = elem.get("Version") or elem.get("version", "")
                # Version alt element olarak da gelebilir
                if not version:
                    for child in elem:
                        ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                        if ctag.lower() == "version" and child.text:
                            version = child.text
                            break
                if name:
                    packages.append({"name": name.strip(), "version": (version or "").strip()})
    except Exception as exc:
        logger.error(f".csproj parse hatası: {exc}")
    return packages


def _parse_pom_xml(content: str) -> list[dict]:
    """Maven — pom.xml"""
    packages: list[dict] = []
    try:
        root = ET.fromstring(content)
        ns_prefix = ""
        if root.tag.startswith("{"):
            ns_prefix = root.tag.split("}")[0] + "}"

        for dep in root.iter(f"{ns_prefix}dependency"):
            group   = dep.find(f"{ns_prefix}groupId")
            artifact = dep.find(f"{ns_prefix}artifactId")
            version  = dep.find(f"{ns_prefix}version")
            if group is not None and artifact is not None:
                ver_text = (version.text or "") if version is not None else ""
                # ${property} gibi dinamik versiyonları atla
                if ver_text.startswith("${"):
                    ver_text = ""
                packages.append({
                    "name": f"{group.text}:{artifact.text}",
                    "version": ver_text.strip(),
                })
    except Exception as exc:
        logger.error(f"pom.xml parse hatası: {exc}")
    return packages


def _parse_go_mod(content: str) -> list[dict]:
    """Go modules — go.mod"""
    packages: list[dict] = []
    in_block = False
    for raw in content.splitlines():
        line = raw.strip()
        # Tek satır require
        if line.startswith("require ") and "(" not in line:
            parts = line.split()
            if len(parts) >= 3:
                packages.append({"name": parts[1], "version": parts[2]})
            continue
        if line.startswith("require ("):
            in_block = True
            continue
        if in_block:
            if line == ")":
                in_block = False
                continue
            # "github.com/foo/bar v1.2.3 // indirect"
            parts = line.split()
            if len(parts) >= 2 and not parts[0].startswith("//"):
                packages.append({"name": parts[0], "version": parts[1]})
    return packages


def _parse_cargo_lock(content: str) -> list[dict]:
    """crates.io — Cargo.lock"""
    packages: list[dict] = []
    current: dict = {}
    for raw in content.splitlines():
        line = raw.strip()
        if line == "[[package]]":
            if current.get("name"):
                packages.append({
                    "name": current["name"],
                    "version": current.get("version", ""),
                })
            current = {}
        elif line.startswith("name = "):
            current["name"] = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("version = "):
            current["version"] = line.split("=", 1)[1].strip().strip('"')
    if current.get("name"):
        packages.append({"name": current["name"], "version": current.get("version", "")})
    return packages


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _severity_from_cvss(score: float) -> str:
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    return "LOW"


def _extract_fixed_version(vuln: dict) -> str:
    for affected in vuln.get("affected", []):
        for rng in affected.get("ranges", []):
            for event in rng.get("events", []):
                if "fixed" in event:
                    return event["fixed"]
    return "bilinmiyor"


def _query_osv(packages: list[dict], ecosystem: str) -> list[dict]:
    """OSV.dev Batch API'ye sorgu atar, bulgular listesi döner."""
    if not packages:
        return []
    queries = [
        {
            "package": {"name": p["name"], "ecosystem": ecosystem},
            **({"version": p["version"]} if p.get("version") else {}),
        }
        for p in packages
    ]
    try:
        resp = requests.post(OSV_BATCH_URL, json={"queries": queries}, timeout=OSV_TIMEOUT)
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except requests.RequestException as exc:
        logger.error(f"OSV API hatası ({ecosystem}): {exc}")
        return []

    findings: list[dict] = []
    for pkg, result in zip(packages, results):
        for vuln in result.get("vulns", []):
            severity = "MEDIUM"
            cvss_score = None
            for sev in vuln.get("severity", []):
                if sev.get("type") in ("CVSS_V3", "CVSS_V2"):
                    try:
                        cvss_score = float(sev.get("score", 0))
                        severity = _severity_from_cvss(cvss_score)
                    except (TypeError, ValueError):
                        pass
                    break
            findings.append({
                "type": "SCA",
                "package": pkg["name"],
                "version": pkg.get("version") or "?",
                "ecosystem": ecosystem,
                "vuln_id": vuln.get("id", "?"),
                "severity": severity,
                "cvss_score": cvss_score,
                "summary": vuln.get("summary") or "Açıklama yok",
                "fixed_in": _extract_fixed_version(vuln),
                "aliases": vuln.get("aliases", []),
            })
    return findings


def _find_all(all_files: list[str], suffix: str) -> list[str]:
    """Verilen suffix ile biten tüm dosyaları döner."""
    return [f for f in all_files if f.endswith(suffix)]


# ---------------------------------------------------------------------------
# Ana fonksiyon
# ---------------------------------------------------------------------------

def analyze_dependencies(
    repo_url: str,
    token: str,
    all_files: list[str],
    get_file_content_fn: Callable,
) -> dict:
    """
    Desteklenen tüm ekosistemler için bağımlılık analizi yapar.
    OSV.dev Batch API kullanılır.
    """
    from app.github.github_service import find_file_path

    if not all_files:
        return {
            "packages_checked": 0,
            "findings": [],
            "skipped_reason": "Repo dosya listesi alınamadı — GitHub token ekleyip tekrar deneyin",
        }

    findings: list[dict] = []
    packages_checked = 0
    dep_files_found = False

    # ── PyPI ──────────────────────────────────────────────────────────
    req_path = find_file_path(all_files, "requirements.txt")
    if req_path:
        dep_files_found = True
        content = get_file_content_fn(repo_url, token, req_path)
        if content:
            pkgs = _parse_requirements(content)
            packages_checked += len(pkgs)
            findings.extend(_query_osv(pkgs, "PyPI"))

    # ── npm ───────────────────────────────────────────────────────────
    pkg_path = find_file_path(all_files, "package.json")
    if pkg_path:
        dep_files_found = True
        content = get_file_content_fn(repo_url, token, pkg_path)
        if content:
            pkgs = _parse_package_json(content)
            packages_checked += len(pkgs)
            findings.extend(_query_osv(pkgs, "npm"))

    # ── NuGet (.csproj) ───────────────────────────────────────────────
    csproj_files = _find_all(all_files, ".csproj")
    if csproj_files:
        dep_files_found = True
        for csproj_path in csproj_files[:5]:   # en fazla 5 proje dosyası
            content = get_file_content_fn(repo_url, token, csproj_path)
            if content:
                pkgs = _parse_csproj(content)
                packages_checked += len(pkgs)
                findings.extend(_query_osv(pkgs, "NuGet"))

    # ── Maven (pom.xml) ───────────────────────────────────────────────
    pom_path = find_file_path(all_files, "pom.xml")
    if pom_path:
        dep_files_found = True
        content = get_file_content_fn(repo_url, token, pom_path)
        if content:
            pkgs = _parse_pom_xml(content)
            packages_checked += len(pkgs)
            findings.extend(_query_osv(pkgs, "Maven"))

    # ── Go (go.mod) ───────────────────────────────────────────────────
    gomod_path = find_file_path(all_files, "go.mod")
    if gomod_path:
        dep_files_found = True
        content = get_file_content_fn(repo_url, token, gomod_path)
        if content:
            pkgs = _parse_go_mod(content)
            packages_checked += len(pkgs)
            findings.extend(_query_osv(pkgs, "Go"))

    # ── Rust (Cargo.lock) ─────────────────────────────────────────────
    cargo_lock_path = find_file_path(all_files, "Cargo.lock")
    if cargo_lock_path:
        dep_files_found = True
        content = get_file_content_fn(repo_url, token, cargo_lock_path)
        if content:
            pkgs = _parse_cargo_lock(content)
            packages_checked += len(pkgs)
            findings.extend(_query_osv(pkgs, "crates.io"))

    result: dict = {"packages_checked": packages_checked, "findings": findings}
    if packages_checked == 0:
        if dep_files_found:
            result["skipped_reason"] = "Bağımlılık dosyaları boş veya okunamadı"
        else:
            result["skipped_reason"] = (
                "Desteklenen bağımlılık dosyası bulunamadı "
                "(requirements.txt, package.json, *.csproj, pom.xml, go.mod, Cargo.lock)"
            )
    logger.info(f"SCA tamamlandı: {packages_checked} paket, {len(findings)} bulgu")
    return result


# ---------------------------------------------------------------------------
# Lokal dizinden okuma (temp_dir varsa GitHub API'ye gerek yok)
# ---------------------------------------------------------------------------

_DEP_FILES = {
    "requirements.txt": ("PyPI",      _parse_requirements),
    "package.json":     ("npm",       _parse_package_json),
    "pom.xml":          ("Maven",     _parse_pom_xml),
    "go.mod":           ("Go",        _parse_go_mod),
    "Cargo.lock":       ("crates.io", _parse_cargo_lock),
}


def analyze_dependencies_from_dir(repo_dir: str) -> dict:
    """
    İndirilmiş repo dizininden bağımlılık dosyalarını okur, OSV.dev'e sorar.
    GitHub API çağrısı yapmaz — temp_dir varken kullanılır.
    """
    import os

    findings: list[dict] = []
    packages_checked = 0
    dep_files_found = False

    for root, _, files in os.walk(repo_dir):
        # node_modules ve sanal ortamları atla
        rel_root = os.path.relpath(root, repo_dir)
        if any(skip in rel_root for skip in ("node_modules", ".venv", "venv", ".git")):
            continue

        for fname in files:
            # .csproj ayrı ele alınacak
            if fname.endswith(".csproj"):
                dep_files_found = True
                fpath = os.path.join(root, fname)
                try:
                    content = open(fpath, encoding="utf-8", errors="ignore").read()
                    pkgs = _parse_csproj(content)
                    packages_checked += len(pkgs)
                    findings.extend(_query_osv(pkgs, "NuGet"))
                except OSError:
                    pass
                continue

            if fname not in _DEP_FILES:
                continue

            ecosystem, parser = _DEP_FILES[fname]
            dep_files_found = True
            fpath = os.path.join(root, fname)
            try:
                content = open(fpath, encoding="utf-8", errors="ignore").read()
                pkgs = parser(content)
                packages_checked += len(pkgs)
                findings.extend(_query_osv(pkgs, ecosystem))
            except OSError as exc:
                logger.warning("Bağımlılık dosyası okunamadı (%s): %s", fpath, exc)

    result: dict = {"packages_checked": packages_checked, "findings": findings}
    if packages_checked == 0:
        result["skipped_reason"] = (
            "Desteklenen bağımlılık dosyası bulunamadı" if not dep_files_found
            else "Bağımlılık dosyaları boş veya okunamadı"
        )
    logger.info("SCA (local) tamamlandı: %d paket, %d bulgu", packages_checked, len(findings))
    return result
