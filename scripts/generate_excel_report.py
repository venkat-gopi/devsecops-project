#!/usr/bin/env python3
"""
Converts all JSON scan reports to a single styled Excel workbook.
Each scan tool gets its own sheet.
Color coding: Red=Critical, Orange=High, Yellow=Medium, Green=Low
"""

import os
import json
import argparse
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment,
    Border, Side
)
from openpyxl.utils import get_column_letter

# ── COLORS ────────────────────────────────────────────────
COLORS = {
    "CRITICAL": {"fill": "FFDC2626", "font": "FFFFFFFF"},
    "HIGH":     {"fill": "FFEA580C", "font": "FFFFFFFF"},
    "MEDIUM":   {"fill": "FFFEF08A", "font": "FF78350F"},
    "LOW":      {"fill": "FFD1FAE5", "font": "FF14532D"},
    "INFO":     {"fill": "FFE0F2FE", "font": "FF0C4A6E"},
    "PASS":     {"fill": "FFD1FAE5", "font": "FF14532D"},
    "FAIL":     {"fill": "FFFECACA", "font": "FF991B1B"},
    "HEADER":   {"fill": "FF111827", "font": "FFFFFFFF"},
    "SUBHEADER":{"fill": "FF374151", "font": "FFFFFFFF"},
    "ALT_ROW":  {"fill": "FFF9FAFB", "font": "FF111827"},
    "WHITE":    {"fill": "FFFFFFFF", "font": "FF111827"},
}

def make_fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def make_font(hex_color, bold=False, size=11):
    return Font(color=hex_color, bold=bold, size=size,
                name="Calibri")

def make_border():
    side = Side(style="thin", color="FFD1D5DB")
    return Border(left=side, right=side, top=side, bottom=side)

def style_cell(cell, severity_or_type="WHITE",
               bold=False, center=False):
    c = COLORS.get(str(severity_or_type).upper(), COLORS["WHITE"])
    cell.fill    = make_fill(c["fill"])
    cell.font    = make_font(c["font"], bold=bold)
    cell.border  = make_border()
    cell.alignment = Alignment(
        horizontal="center" if center else "left",
        vertical="center", wrap_text=True
    )

def write_header_row(ws, headers, row=1):
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        style_cell(cell, "HEADER", bold=True, center=True)
    ws.row_dimensions[row].height = 22

def auto_column_width(ws, min_width=12, max_width=50):
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        width = min(max(min_width, max_len + 4), max_width)
        ws.column_dimensions[col_letter].width = width

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None

# ── SHEET BUILDERS ────────────────────────────────────────

def build_summary_sheet(ws, app_name, run_id, counts):
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 20

    ws.merge_cells("A1:B1")
    cell = ws["A1"]
    cell.value = f"Security Scan Report — {app_name}"
    cell.font  = Font(bold=True, size=14, color="FF111827", name="Calibri")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:B2")
    ws["A2"].value = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
    ws["A2"].font  = Font(size=10, color="FF6B7280", name="Calibri")
    ws["A2"].alignment = Alignment(horizontal="center")

    ws.append([])

    headers = ["Category", "Count"]
    write_header_row(ws, headers, row=4)

    summary_data = [
        ("Critical Vulnerabilities", counts.get("critical", 0), "CRITICAL"),
        ("High Vulnerabilities",     counts.get("high", 0),     "HIGH"),
        ("Medium Vulnerabilities",   counts.get("medium", 0),   "MEDIUM"),
        ("Low Vulnerabilities",      counts.get("low", 0),      "LOW"),
        ("Secrets Found",            counts.get("secrets", 0),  "CRITICAL"),
        ("IaC Misconfigs",           counts.get("iac", 0),      "HIGH"),
        ("OPA Policy Result",        counts.get("opa", 0),      "PASS" if counts.get("opa_allow", False) else "FAIL"),
        ("Total Issues",             counts.get("total", 0),    "SUBHEADER"),
    ]

    for row_idx, (label, count, severity) in enumerate(summary_data, 5):
        ws.cell(row=row_idx, column=1, value=label)
        ws.cell(row=row_idx, column=2, value=count)
        style_cell(ws.cell(row=row_idx, column=1), severity)
        style_cell(ws.cell(row=row_idx, column=2), severity, center=True)
        ws.row_dimensions[row_idx].height = 20

    ws.append([])
    ws.append(["Pipeline Run ID", run_id])
    ws.append(["Report Format", "Excel (.xlsx) - DevSecOps Pipeline"])


def build_secrets_sheet(ws, reports_dir):
    headers = ["Rule ID", "Severity", "File", "Line", "Match", "Commit", "Author"]
    write_header_row(ws, headers)

    gl_path = os.path.join(reports_dir, "gitleaks-report.json")
    data = load_json(gl_path)

    if not data or not isinstance(data, list):
        ws.append(["No secrets detected", "", "", "", "", "", ""])
        style_cell(ws.cell(row=2, column=1), "PASS")
        auto_column_width(ws)
        return 0

    count = 0
    for idx, leak in enumerate(data):
        row_num = idx + 2
        row_data = [
            leak.get("RuleID", "N/A"),
            "CRITICAL",
            leak.get("File", "N/A"),
            str(leak.get("StartLine", "N/A")),
            str(leak.get("Match", ""))[:50] + "...",
            str(leak.get("Commit", "N/A"))[:12],
            leak.get("Author", "N/A")
        ]
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col, value=val)
            style_cell(cell, "CRITICAL" if col == 2
                       else ("ALT_ROW" if idx % 2 == 0 else "WHITE"))
        ws.row_dimensions[row_num].height = 20
        count += 1

    auto_column_width(ws)
    return count


def build_dependencies_sheet(ws, reports_dir):
    headers = ["Source", "Severity", "Package", "Vulnerability", "Installed Version", "Fix Version", "CVE"]
    write_header_row(ws, headers)

    rows = []

    snyk = load_json(os.path.join(reports_dir, "snyk-report.json"))
    if snyk and "vulnerabilities" in snyk:
        vulns = snyk["vulnerabilities"]
        if isinstance(vulns, list):
            for v in vulns:
                rows.append([
                    "Snyk",
                    str(v.get("severity", "unknown")).upper(),
                    v.get("packageName", "N/A"),
                    v.get("title", "N/A"),
                    v.get("version", "N/A"),
                    ", ".join(v.get("fixedIn", ["No fix"])),
                    v.get("identifiers", {}).get("CVE", ["N/A"])[0]
                      if v.get("identifiers") else "N/A"
                ])

    npm = load_json(os.path.join(reports_dir, "npm-audit.json"))
    if npm and "vulnerabilities" in npm:
        vulns = npm["vulnerabilities"]
        if isinstance(vulns, dict):
            for pkg, info in vulns.items():
                fix = info.get("fixAvailable", {})
                rows.append([
                    "npm audit",
                    str(info.get("severity", "unknown")).upper(),
                    pkg,
                    info.get("title", "Vulnerability"),
                    info.get("range", "N/A"),
                    fix.get("version", "N/A")
                      if isinstance(fix, dict) else "N/A",
                    "N/A"
                ])

    if not rows:
        ws.append(["No dependency vulnerabilities found", "", "", "", "", "", ""])
        style_cell(ws.cell(row=2, column=1), "PASS")
        auto_column_width(ws)
        return 0

    for idx, row_data in enumerate(rows):
        row_num = idx + 2
        severity = row_data[1]
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col, value=val)
            style_cell(cell, severity if col == 2
                       else ("ALT_ROW" if idx % 2 == 0 else "WHITE"))
        ws.row_dimensions[row_num].height = 20

    auto_column_width(ws)
    return len(rows)


def build_container_sheet(ws, reports_dir):
    headers = ["CVE ID", "Severity", "Package", "Installed", "Fixed Version", "Description"]
    write_header_row(ws, headers)

    trivy = load_json(os.path.join(reports_dir, "trivy-report.json"))
    rows = []

    if trivy:
        for result in trivy.get("Results", []):
            for vuln in (result.get("Vulnerabilities") or []):
                rows.append([
                    vuln.get("VulnerabilityID", "N/A"),
                    vuln.get("Severity", "UNKNOWN"),
                    vuln.get("PkgName", "N/A"),
                    vuln.get("InstalledVersion", "N/A"),
                    vuln.get("FixedVersion", "No fix"),
                    vuln.get("Title", "N/A")[:80]
                ])

    if not rows:
        ws.append(["No container vulnerabilities found", "", "", "", "", ""])
        style_cell(ws.cell(row=2, column=1), "PASS")
        auto_column_width(ws)
        return 0

    for idx, row_data in enumerate(rows):
        row_num = idx + 2
        severity = row_data[1]
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col, value=val)
            style_cell(cell, severity if col == 2
                       else ("ALT_ROW" if idx % 2 == 0 else "WHITE"))
        ws.row_dimensions[row_num].height = 20

    auto_column_width(ws)
    return len(rows)


def build_iac_sheet(ws, reports_dir):
    headers = ["Check ID", "Severity", "Resource", "File", "Description", "Guideline"]
    write_header_row(ws, headers)

    checkov = load_json(os.path.join(reports_dir, "checkov-report.json"))
    rows = []

    if checkov:
        failed = checkov.get("results", {}).get("failed_checks", [])
        for check in failed:
            rows.append([
                check.get("check_id", "N/A"),
                "HIGH",
                check.get("resource", "N/A"),
                check.get("file_path", "N/A"),
                check.get("check_result", {}).get("result", "FAILED"),
                check.get("guideline", "N/A")[:80]
            ])

    if not rows:
        ws.append(["No IaC issues found", "", "", "", "", ""])
        style_cell(ws.cell(row=2, column=1), "PASS")
        auto_column_width(ws)
        return 0

    for idx, row_data in enumerate(rows):
        row_num = idx + 2
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col, value=val)
            style_cell(cell, "HIGH" if col == 2
                       else ("ALT_ROW" if idx % 2 == 0 else "WHITE"))
        ws.row_dimensions[row_num].height = 20

    auto_column_width(ws)
    return len(rows)


def build_opa_sheet(ws, reports_dir):
    headers = ["Decision", "Result", "Reason", "Input File"]
    write_header_row(ws, headers)

    opa = load_json(os.path.join(reports_dir, "opa-result.json"))
    if not opa:
        ws.append(["No OPA decision report found", "", "", ""])
        style_cell(ws.cell(row=2, column=1), "PASS")
        auto_column_width(ws)
        return False

    allow = bool(opa.get("allow", False))
    deny = opa.get("deny") or opa.get("denies") or []
    if isinstance(deny, dict):
        deny = list(deny.values())

    reason = "Policy passed" if allow else ("; ".join([str(x) for x in deny]) if deny else "Policy blocked")
    row_data = ["OPA Policy Gate", "ALLOW" if allow else "DENY", reason, "opa-result.json"]
    for col, val in enumerate(row_data, 1):
        cell = ws.cell(row=2, column=col, value=val)
        style_cell(cell, "PASS" if allow else "FAIL" if col == 2 else "WHITE", bold=(col == 1), center=(col == 2))
    ws.row_dimensions[2].height = 24
    auto_column_width(ws)
    return allow


def count_from_scan_summary(path):
    data = load_json(path)
    if not data:
        return {}
    return {
        "critical": int(data.get("critical", 0) or 0),
        "high": int(data.get("high", 0) or 0),
        "medium": int(data.get("medium", 0) or 0),
        "low": int(data.get("low", 0) or 0),
        "secrets": int(data.get("secrets", 0) or 0),
        "iac": int(data.get("iac", 0) or 0),
        "total": int(data.get("total", 0) or 0),
        "opa": int(data.get("opa", 1) or 0),
        "opa_allow": bool(data.get("opa_allow", False)),
    }

# ── MAIN ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", required=True)
    parser.add_argument("--app-name",    required=True)
    parser.add_argument("--run-id",      default="local")
    parser.add_argument("--output",      required=True)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    counts = count_from_scan_summary(os.path.join(args.reports_dir, "scan-summary.json"))

    wb = Workbook()

    ws_summary = wb.active
    ws_summary.title = "Summary"

    ws_secrets = wb.create_sheet("GitLeaks Secrets")
    ws_deps    = wb.create_sheet("Dependencies")
    ws_cont    = wb.create_sheet("Container Trivy")
    ws_iac     = wb.create_sheet("Checkov IaC")
    ws_opa     = wb.create_sheet("OPA Policy Gate")

    secrets_count = build_secrets_sheet(ws_secrets, args.reports_dir)
    deps_count    = build_dependencies_sheet(ws_deps, args.reports_dir)
    cont_count    = build_container_sheet(ws_cont, args.reports_dir)
    iac_count     = build_iac_sheet(ws_iac, args.reports_dir)
    opa_allow     = build_opa_sheet(ws_opa, args.reports_dir)

    if not counts:
        counts = {
            "critical": secrets_count,
            "high": deps_count,
            "medium": cont_count,
            "low": 0,
            "secrets": secrets_count,
            "iac": iac_count,
            "total": secrets_count + deps_count + cont_count + iac_count,
            "opa": 1,
            "opa_allow": opa_allow,
        }
    else:
        counts.setdefault("critical", secrets_count)
        counts.setdefault("high", deps_count)
        counts.setdefault("medium", cont_count)
        counts.setdefault("low", 0)
        counts.setdefault("secrets", secrets_count)
        counts.setdefault("iac", iac_count)
        counts.setdefault("total", secrets_count + deps_count + cont_count + iac_count)
        counts.setdefault("opa", 1)
        counts.setdefault("opa_allow", opa_allow)

    build_summary_sheet(ws_summary, args.app_name, args.run_id, counts)
    auto_column_width(ws_summary)

    wb.save(args.output)
    print(f"Excel report saved: {args.output}")
    print(f"Total issues found: {counts['total']}")

if __name__ == "__main__":
    main()

