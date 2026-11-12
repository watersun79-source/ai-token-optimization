"""Audit pinned Python/npm locks against public advisories and installed license metadata."""
import argparse
import importlib.metadata as md
import json
from pathlib import Path
import re
import sys

def norm(x):
    return re.sub(r"[-_.]+", "-", str(x)).lower()

def classification(values):
    values = [str(x) for x in values if x and str(x).strip().lower() not in ("none", "unknown")]
    if not values:
        return "UNVERIFIED"
    if any(re.search(r"\b(?:AGPL|GPL|LGPL|SSPL|BUSL|Proprietary|Noncommercial)", v, re.I) for v in values):
        return "REVIEW"
    return "DECLARED"

def analyze_python(lock, report):
    lines = [x.strip() for x in lock.read_text().splitlines() if x.strip()]
    packages = {}
    for line in lines:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+", line):
            raise ValueError("not fully pinned")
        name, version = line.split("==", 1)
        if norm(name) in packages:
            raise ValueError("duplicate normalized dependency")
        packages[norm(name)] = version
    results = report.get("dependencies")
    if not isinstance(results, list):
        raise ValueError("official advisory response missing dependencies")
    matched, findings = set(), []
    for entry in results:
        name, version = norm(entry.get("name", "")), str(entry.get("version", ""))
        if name not in packages or version != packages[name] or name in matched:
            raise ValueError("advisory version/identity mismatch")
        matched.add(name)
        for vuln in entry.get("vulns", []):
            findings.append({"package": name, "version": version,
                             "id": vuln.get("id"), "fix_versions": vuln.get("fix_versions", [])[:5]})
    if matched != set(packages):
        raise ValueError("official advisory coverage incomplete")
    licenses = []
    for name, version in packages.items():
        try:
            d = md.distribution(name)
            if d.version != version:
                raise ValueError("installed version mismatch: " + name)
            m = d.metadata
            values = [m.get("License-Expression"), m.get("License")]
            values += [x for x in m.get_all("Classifier", []) if x.startswith("License ::")]
            status = classification(values)
        except md.PackageNotFoundError:
            status = "UNVERIFIED"
        licenses.append((name, status))
    return len(packages), len(matched), findings, licenses

def analyze_npm(lock, report, root):
    document = json.loads(lock.read_text())
    packages = document.get("packages")
    if not isinstance(packages, dict) or len(packages) < 2:
        raise ValueError("npm lock missing packages")
    if "error" in report or not isinstance(report.get("vulnerabilities"), dict):
        raise ValueError("npm official advisories not available")
    findings = []
    for name, v in report["vulnerabilities"].items():
        findings.append({"package": name, "severity": v.get("severity"),
                         "advisories": [a.get("url") for a in v.get("via", []) if isinstance(a, dict)][:5],
                         "fix_available": v.get("fixAvailable")})
    licenses = []
    for rel, spec in packages.items():
        if not rel:
            continue
        name = spec.get("name") or rel.split("node_modules/")[-1]
        try:
            obj = json.loads((root / rel / "package.json").read_text())
            status = classification([obj.get("license"), obj.get("licenses")])
            if obj.get("version") != spec.get("version"):
                status = "UNVERIFIED"
        except (OSError, ValueError):
            status = "UNVERIFIED"
        licenses.append((name, status))
    return len(packages)-1, len(packages)-1, findings, licenses

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=("python", "npm"), required=True)
    p.add_argument("--lock", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--exit-code", type=int, required=True)
    p.add_argument("--root", type=Path, default=Path("."))
    a = p.parse_args()
    try:
        if a.exit_code not in (0, 1):
            raise ValueError("audit service did not complete successfully")
        report = json.loads(a.audit.read_text())
        size, covered, findings, licenses = (analyze_python(a.lock, report)
            if a.kind == "python" else analyze_npm(a.lock, report, a.root))
        if (a.exit_code == 0) != (len(findings) == 0):
            raise ValueError("official audit exit contradicts findings")
        receipt = {"kind": a.kind, "lock": a.lock.name,
                   "dependencies": size, "audited": covered,
                   "known_advisories": len(findings), "findings": findings[:20],
                   "findings_truncated": len(findings) > 20,
                   "license_declared": sum(s == "DECLARED" for _, s in licenses),
                   "license_review": [n for n,s in licenses if s == "REVIEW"][:20],
                   "license_unknown": [n for n,s in licenses if s == "UNVERIFIED"][:20],
                   "license_scope": "METADATA_ONLY_NOT_LEGAL_APPROVAL",
                   "external_ai_calls": 0, "production_writes": 0,
                   "status": "KNOWN_VULNERABILITIES" if findings else "NO_KNOWN_ADVISORIES"}
        code = 1 if findings else 0
    except (OSError, ValueError, KeyError, TypeError) as e:
        receipt = {"status": "UNVERIFIED", "reason": type(e).__name__, "detail": str(e)[:160]}
        code = 2
    print("OSS_SECURITY_RECEIPT=" + json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return code

if __name__ == "__main__":
    sys.exit(main())
