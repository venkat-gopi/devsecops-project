#!/usr/bin/env python3

import os
import json
import argparse


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    reports_dir = args.reports_dir

    critical = 0
    high = 0
    medium = 0
    low = 0
    secrets = 0

    # GitLeaks
    gitleaks = load_json(os.path.join(reports_dir, "gitleaks-report.json"))
    if isinstance(gitleaks, list):
        secrets = len(gitleaks)
        critical += secrets

    # npm audit
    npm = load_json(os.path.join(reports_dir, "npm-audit.json"))
    if isinstance(npm, dict):
        meta = npm.get("metadata", {}).get("vulnerabilities", {})
        critical += int(meta.get("critical", 0))
        high += int(meta.get("high", 0))
        medium += int(meta.get("moderate", 0))
        low += int(meta.get("low", 0))

    # Snyk
    snyk = load_json(os.path.join(reports_dir, "snyk-report.json"))
    if isinstance(snyk, dict):
        for vuln in snyk.get("vulnerabilities", []):
            severity = vuln.get("severity", "").lower()
            if severity == "critical":
                critical += 1
            elif severity == "high":
                high += 1
            elif severity == "medium":
                medium += 1
            elif severity == "low":
                low += 1

    # Trivy
    trivy = load_json(os.path.join(reports_dir, "trivy-report.json"))
    if isinstance(trivy, dict):
        trivy_status = str(trivy.get("status", "")).lower()

        if trivy_status in ["docker_build_failed", "dockerfile_missing"]:
            critical += 1

        for result in trivy.get("Results", []):
            for vuln in result.get("Vulnerabilities") or []:
                severity = vuln.get("Severity", "").upper()
                if severity == "CRITICAL":
                    critical += 1
                elif severity == "HIGH":
                    high += 1
                elif severity == "MEDIUM":
                    medium += 1
                elif severity == "LOW":
                    low += 1
    # Checkov
    checkov = load_json(os.path.join(reports_dir, "checkov-report.json"))
 
    if isinstance(checkov, dict):
        failed = checkov.get("results", {}).get("failed_checks", [])
        if isinstance(failed, list):
            high += len(failed)

    elif isinstance(checkov, list):
        for block in checkov:
            if isinstance(block, dict):
                failed = block.get("results", {}).get("failed_checks", [])
                if isinstance(failed, list):
                    high += len(failed)
    result = {
        "critical_count": critical,
        "high_count": high,
        "medium_count": medium,
        "low_count": low,
        "secrets_count": secrets,
        "total_count": critical + high + medium + low,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
