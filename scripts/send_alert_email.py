#!/usr/bin/env python3
"""
Sends HTML vulnerability alert email via SendGrid.
Called by GitHub Actions when scans detect vulnerabilities.
"""

import os
import json
import argparse
from datetime import datetime

# ────────────────────────────────────────────────────────────
def load_json_safely(filepath):
    try:
        with open(filepath) as f:
            return json.load(f)
    except Exception:
        return {}

# ────────────────────────────────────────────────────────────
def build_vulnerability_rows(reports_dir):
    """Read all scan JSONs and return HTML table rows."""
    rows = []

    # From Snyk
    snyk_path = os.path.join(reports_dir, "snyk-report.json")
    if os.path.exists(snyk_path):
        data = load_json_safely(snyk_path)
        for v in data.get("vulnerabilities", [])[:10]:
            rows.append({
                "source":    "Snyk",
                "severity":  v.get("severity", "unknown").upper(),
                "package":   v.get("packageName", "N/A"),
                "issue":     v.get("title", "N/A"),
                "fix":       v.get("fixedIn", ["No fix"])[0] if v.get("fixedIn") else "No fix available"
            })

    # From npm audit
    npm_path = os.path.join(reports_dir, "npm-audit.json")
    if os.path.exists(npm_path):
        data = load_json_safely(npm_path)
        for name, info in list(data.get("vulnerabilities", {}).items())[:10]:
            rows.append({
                "source":   "npm audit",
                "severity": info.get("severity", "unknown").upper(),
                "package":  name,
                "issue":    info.get("title", "Vulnerability found"),
                "fix":      f"v{info.get('fixAvailable', {}).get('version', 'N/A')}"
                             if isinstance(info.get("fixAvailable"), dict) else "N/A"
            })

    # From Trivy
    trivy_path = os.path.join(reports_dir, "trivy-report.json")
    if os.path.exists(trivy_path):
        data = load_json_safely(trivy_path)

        status = str(data.get("status", "")).lower()
        if status in ["docker_build_failed", "dockerfile_missing"]:
            rows.append({
                "source": "Trivy",
                "severity": "CRITICAL",
                "package": "Docker Build",
                "issue": data.get("message", "Container image build failed"),
                "fix": "Fix Dockerfile path, package files, build context, or dependency install command"
            })

        for result in data.get("Results", []):
            for v in (result.get("Vulnerabilities") or [])[:5]:
                rows.append({
                    "source":   "Trivy",
                    "severity": v.get("Severity", "UNKNOWN"),
                    "package":  v.get("PkgName", "N/A"),
                    "issue":    v.get("VulnerabilityID", "N/A"),
                    "fix":      v.get("FixedVersion", "No fix available")
                })

    # From GitLeaks
    gl_path = os.path.join(reports_dir, "gitleaks-report.json")
    if os.path.exists(gl_path):
        data = load_json_safely(gl_path)
        leaks = data if isinstance(data, list) else []
        for leak in leaks[:5]:
            rows.append({
                "source":   "GitLeaks",
                "severity": "CRITICAL",
                "package":  leak.get("RuleID", "Secret"),
                "issue":    f"Secret in {leak.get('File', 'unknown file')}",
                "fix":      "Remove secret, rotate credentials immediately"
            })

    # From OPA
    opa_path = os.path.join(reports_dir, "opa-result.json")
    if os.path.exists(opa_path):
        data = load_json_safely(opa_path)
        decision = data.get("allow", False)
        rows.append({
            "source":   "OPA Policy",
            "severity": "CRITICAL" if not decision else "LOW",
            "package":  "Policy Gate",
            "issue":    "Policy failed" if not decision else "Policy passed",
            "fix":      "Review policy violations and rerun pipeline" if not decision else "No action needed"
        })

    return rows

# ────────────────────────────────────────────────────────────
def get_severity_color(severity):
    return {
        "CRITICAL": "#dc2626",
        "HIGH":     "#ea580c",
        "MEDIUM":   "#ca8a04",
        "LOW":      "#16a34a",
    }.get(severity.upper(), "#6b7280")

# ────────────────────────────────────────────────────────────
def build_html_email(app_name, critical, high, medium,
                     pipeline_url, rows):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    # Build vulnerability table rows
    table_rows_html = ""
    for row in rows:
        color = get_severity_color(row["severity"])
        table_rows_html += f"""
        <tr>
          <td style="padding:8px;border:1px solid #e5e7eb">{row['source']}</td>
          <td style="padding:8px;border:1px solid #e5e7eb;
                     color:{color};font-weight:bold">{row['severity']}</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{row['package']}</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{row['issue']}</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{row['fix']}</td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;max-width:900px;margin:0 auto;padding:24px">

  <!-- Header -->
  <div style="background:#dc2626;color:white;padding:20px 24px;border-radius:8px 8px 0 0">
    <h2 style="margin:0">Security Vulnerabilities Detected</h2>
    <p style="margin:4px 0 0;opacity:0.9">{app_name} — {timestamp}</p>
  </div>

  <!-- Summary Counts -->
  <div style="display:flex;gap:12px;padding:20px;background:#fef2f2;border:1px solid #fecaca">
    <div style="flex:1;text-align:center;padding:16px;background:white;
                border-radius:8px;border-left:4px solid #dc2626">
      <div style="font-size:32px;font-weight:bold;color:#dc2626">{critical}</div>
      <div style="color:#6b7280;margin-top:4px">Critical</div>
    </div>
    <div style="flex:1;text-align:center;padding:16px;background:white;
                border-radius:8px;border-left:4px solid #ea580c">
      <div style="font-size:32px;font-weight:bold;color:#ea580c">{high}</div>
      <div style="color:#6b7280;margin-top:4px">High</div>
    </div>
    <div style="flex:1;text-align:center;padding:16px;background:white;
                border-radius:8px;border-left:4px solid #ca8a04">
      <div style="font-size:32px;font-weight:bold;color:#ca8a04">{medium}</div>
      <div style="color:#6b7280;margin-top:4px">Medium</div>
    </div>
  </div>

  <!-- Pipeline Action Buttons -->
  <div style="padding:24px;background:#f9fafb;border:1px solid #e5e7eb;
              border-top:none;text-align:center">
    <p style="color:#374151;margin-bottom:16px">
      <strong>Action Required:</strong> The deployment pipeline is paused.
      Review the vulnerabilities below and choose an action.
    </p>

    <!-- Approve Button -->
    <a href="{pipeline_url}"
       style="display:inline-block;padding:12px 32px;background:#16a34a;
              color:white;text-decoration:none;border-radius:6px;
              font-weight:bold;font-size:16px;margin:0 8px">
      Review and Approve Deployment
    </a>

    <!-- View Details Button -->
    <a href="{pipeline_url}"
       style="display:inline-block;padding:12px 32px;background:#2563eb;
              color:white;text-decoration:none;border-radius:6px;
              font-weight:bold;font-size:16px;margin:0 8px">
      View Full Pipeline Details
    </a>
  </div>

  <!-- Approval Instructions -->
  <div style="padding:16px;background:#fffbeb;border:1px solid #fde68a;border-top:none">
    <p style="margin:0;color:#92400e;font-size:13px">
      <strong>How to approve:</strong>
      Click "Review and Approve Deployment" above → scroll to the
      <em>manual-approval</em> job → click <strong>Review deployments</strong>
      → check the box → click <strong>Approve and deploy</strong>.
    </p>
  </div>

  <!-- Vulnerability Table -->
  <div style="padding:24px 0">
    <h3 style="color:#111827">Vulnerability Details</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#111827;color:white">
          <th style="padding:10px;text-align:left;border:1px solid #374151">Source</th>
          <th style="padding:10px;text-align:left;border:1px solid #374151">Severity</th>
          <th style="padding:10px;text-align:left;border:1px solid #374151">Package</th>
          <th style="padding:10px;text-align:left;border:1px solid #374151">Issue</th>
          <th style="padding:10px;text-align:left;border:1px solid #374151">Fix</th>
        </tr>
      </thead>
      <tbody>
        {table_rows_html}
      </tbody>
    </table>
  </div>

  <!-- Footer -->
  <div style="padding:16px;background:#f3f4f6;border-radius:0 0 8px 8px;
              font-size:12px;color:#6b7280;text-align:center">
    Generated by DevSecOps Pipeline | {app_name} |
    <a href="{pipeline_url}" style="color:#2563eb">View Pipeline Run</a>
  </div>

</body>
</html>"""

# ────────────────────────────────────────────────────────────
def send_email(to, from_email, subject, html_content, attachment_paths=None):
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import (
            Mail, Attachment, FileContent,
            FileName, FileType, Disposition
        )
        import base64

        message = Mail(
            from_email=from_email,
            to_emails=to,
            subject=subject,
            html_content=html_content
        )

        if attachment_paths:
            attachments = []

            for attachment_path in attachment_paths:
                if not os.path.exists(attachment_path):
                    continue

                with open(attachment_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()

                attachment = Attachment(
                    FileContent(encoded),
                    FileName(os.path.basename(attachment_path)),
                    FileType(
                        "application/vnd.openxmlformats-officedocument"
                        ".spreadsheetml.sheet"
                    ),
                    Disposition("attachment")
                )

                attachments.append(attachment)

            if attachments:
                message.attachment = attachments

        sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
        response = sg.send(message)
        print(f"Email sent. Status: {response.status_code}")
        return True

    except Exception as e:
        print(f"Email failed: {e}")
        return False
# ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to",           required=True)
    parser.add_argument("--from-email",   required=True)
    parser.add_argument("--app-name",     required=True)
    parser.add_argument("--critical",     default="0")
    parser.add_argument("--high",         default="0")
    parser.add_argument("--medium",       default="0")
    parser.add_argument("--pipeline-url", required=True)
    parser.add_argument("--reports-dir",  default="reports")
    args = parser.parse_args()

    # Find Excel attachment
    excel_paths = []
    for f in os.listdir(args.reports_dir):
        if f.endswith(".xlsx"):
            excel_paths.append(os.path.join(args.reports_dir, f))

    print(f"Excel reports attached: {len(excel_paths)}")

    rows    = build_vulnerability_rows(args.reports_dir)
    html    = build_html_email(
        args.app_name, args.critical, args.high,
        args.medium, args.pipeline_url, rows
    )
    subject = (f"SECURITY ALERT: {args.app_name} — "
               f"{args.critical} Critical, {args.high} High vulnerabilities found")

    send_email(
        to=args.to,
        from_email=args.from_email,
        subject=subject,
        html_content=html,
        attachment_paths=excel_paths
    )

if __name__ == "__main__":
    main()

