# DevSecOps CI/CD Pipeline with AWS EKS

This project is a complete DevSecOps CI/CD pipeline built using GitHub Actions. It accepts a customer application repository, runs multiple security scans, generates individual Excel reports, applies OPA policy checks, sends email alerts when required, waits for manual approval, builds the Docker image using the customer-provided Dockerfile, pushes the image to Docker Hub, and deploys the application to Amazon EKS.

The main goal of this project is to integrate security into every stage of software delivery instead of treating security as a final manual check.

---

## Project Overview

In a normal CI/CD pipeline, code is often built and deployed directly. In this project, the application is first verified through different security layers before deployment.

The pipeline checks for:

- Hardcoded secrets
- Code vulnerabilities
- Dependency vulnerabilities
- Container image vulnerabilities
- Infrastructure-as-Code misconfigurations
- Policy violations

After scanning, the pipeline generates reports, applies policy decisions, and deploys the application to Amazon EKS only when the build and policy conditions are satisfied.

---

# High-Level Pipeline Flow

```text
Customer Code / Repository
        │
        ▼
GitHub Actions Workflow
        │
        ▼
File Intake + App Type Detection
        │
        ├── Detect Dockerfile
        ├── Detect Application Type
        └── Validate Repository Structure
        │
        ▼
Layer-wise Security Scanning
        │
        ├── GitLeaks Secret Scan
        ├── SonarCloud SAST Analysis
        ├── Dependency Vulnerability Scan
        │      ├── npm audit
        │      ├── Safety
        │      ├── OWASP Dependency Check
        │      └── gosec
        ├── Snyk Scan
        ├── Trivy Container Scan
        └── Checkov IaC Scan
        │
        ▼
Individual Excel Report Generation
        │
        ├── GitLeaks Report.xlsx
        ├── SonarCloud Report.xlsx
        ├── Dependency Report.xlsx
        ├── Snyk Report.xlsx
        ├── Trivy Report.xlsx
        └── Checkov Report.xlsx
        │
        ▼
OPA Policy Gate
        │
        ├──────────────┬────────────────
        │              │
        ▼              ▼
Policy Passed     Policy Failed
        │              │
        ▼              ▼
Deploy to EKS     Email Alert + Manual Approval
        │              │
        └──────► Deploy After Approval
```
                       

## Key Features

- Dynamic customer application intake
- Dockerfile-first image build
- Layer-wise security scanning
- Individual Excel reports for every scan
- Raw JSON reports for audit logs
- OPA policy gate before deployment
- Email alert on policy failure
- Manual approval before risky deployment
- Docker image push to Docker Hub
- Deployment to Amazon EKS
- Dev, staging, and production deployment flow

---

## Security Scans Used

| Layer | Scan Type | Tool Used |
|---|---|---|
| Layer 1 | Secret scanning | GitLeaks |
| Layer 2 | SAST/code scanning | SonarCloud |
| Layer 3 | Dependency scanning | npm audit / Safety |
| Layer 3B | Open-source dependency scanning | Snyk |
| Layer 4 | Container image scanning | Trivy |
| Layer 5 | IaC scanning | Checkov |
| Layer 6 | Policy gate | OPA |

---

## Reports Generated

Each security scan generates a separate Excel report. The project does not depend only on one combined report.

Expected Excel reports:

```text
gitleaks-report.xlsx
sast-sonar-report.xlsx
dependency-report.xlsx
snyk-report.xlsx
trivy-container-report.xlsx
checkov-iac-report.xlsx
opa-policy-report.xlsx
```

Raw JSON reports are also uploaded as GitHub Actions artifacts for debugging and audit purposes.

---

## Policy Gate Logic

OPA is used to evaluate the scan summary before deployment.

Typical policy behavior:

| Case | Result |
|---|---|
| Dockerfile missing | Deployment blocked |
| Docker build fails | Deployment blocked |
| Critical vulnerability found | Policy fails |
| High vulnerability found | Policy fails |
| Secret found | Policy fails |
| Policy fails and reviewer approves | Deployment allowed |
| Docker build fails and reviewer approves | Still blocked |

Manual approval can allow deployment when policy fails, but it cannot override Dockerfile or Docker build failure.

---

## Manual Approval

If vulnerabilities are found, the pipeline sends an email alert and pauses for manual approval.

Manual approval is useful because it allows a reviewer to check the security reports before allowing deployment. This is important in real DevSecOps pipelines because not every vulnerability has the same business impact.

The approval environment used is:

```text
vulnerability-review
```

---

## Deployment Strategy

The final deployment is done on Amazon EKS.

The same Docker image is deployed into three Kubernetes namespaces:

```text
dev
staging
production
```

| Environment | Kubernetes Namespace | Service Type |
|---|---|---|
| Dev | dev | ClusterIP |
| Staging | staging | ClusterIP |
| Production | production | LoadBalancer |

Dev and staging are internal deployments. Production is exposed using a LoadBalancer service.

---

## Why Amazon EKS Is Used

Amazon EKS is used as the final cloud deployment platform. It allows the pipeline to deploy containerized applications into a managed Kubernetes environment.

In this project:

- Docker is used to package the application.
- Docker Hub is used to store the image.
- EKS is used to run the application.
- GitHub Actions automates scanning, approval, build, and deployment.

This makes the project a complete CI/CD DevSecOps pipeline, not just a security scanning workflow.

---

## Repository Structure

```text
devsecops-project/
├── .github/
│   └── workflows/
│       └── dynamic-devsecops-eks.yml
│
├── k8s/
│   ├── deployment.yaml
│   └── service.yaml
│
├── policy/
│   └── deployment_policy.rego
│
├── scripts/
│   ├── compile_scan_results.py
│   ├── detect_app_type.sh
│   ├── dockerfile_first_build.sh
│   ├── generate_individual_excel_reports.py
│   └── send_alert_email.py
│
└── README.md
```

---

## Main Files

| File | Purpose |
|---|---|
| `.github/workflows/dynamic-devsecops-eks.yml` | Main GitHub Actions pipeline |
| `scripts/detect_app_type.sh` | Detects application type for scan visibility |
| `scripts/dockerfile_first_build.sh` | Builds Docker image using customer Dockerfile |
| `scripts/compile_scan_results.py` | Compiles scan counts for OPA policy input |
| `scripts/generate_individual_excel_reports.py` | Generates separate Excel reports for each scan |
| `scripts/send_alert_email.py` | Sends email alert with reports and approval link |
| `policy/deployment_policy.rego` | OPA policy rules |
| `k8s/deployment.yaml` | Kubernetes deployment template |
| `k8s/service.yaml` | Kubernetes service template |

---

## Required GitHub Secrets

The following GitHub secrets are required:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
EKS_CLUSTER_NAME
DOCKER_USERNAME
DOCKER_PASSWORD
SONAR_TOKEN
SONAR_ORG
SNYK_TOKEN
SENDGRID_API_KEY
ALERT_FROM_EMAIL
```

Example:

```bash
gh secret set AWS_REGION --body "ap-south-1"
gh secret set EKS_CLUSTER_NAME --body "devsecops-eks-cluster"
```

---

## GitHub Environment Setup

Create these GitHub environments:

```text
vulnerability-review
dev
staging
production
```

Recommended approval setup:

| Environment | Approval |
|---|---|
| vulnerability-review | Required |
| dev | Not required |
| staging | Optional |
| production | Recommended |

---

## EKS Setup

Install required tools:

```bash
brew install awscli kubectl eksctl
```

Configure AWS:

```bash
aws configure
```

Create the EKS cluster:

```bash
eksctl create cluster \
  --name devsecops-eks-cluster \
  --region ap-south-1 \
  --nodegroup-name devsecops-nodes \
  --node-type t3.small \
  --nodes 1 \
  --nodes-min 1 \
  --nodes-max 1 \
  --managed
```

Connect local terminal to EKS:

```bash
aws eks update-kubeconfig \
  --region ap-south-1 \
  --name devsecops-eks-cluster
```

Verify nodes:

```bash
kubectl get nodes
```

Expected status:

```text
Ready
```

---

## How to Run the Pipeline

1. Open the GitHub repository.
2. Go to the **Actions** tab.
3. Select the DevSecOps workflow.
4. Click **Run workflow**.
5. Provide the required inputs:
   - Application name
   - Customer source
   - Customer repository URL
   - Application type
   - Customer email
   - Deployment environment
6. Wait for scans, reports, approval, image build, and EKS deployment.

---

## How to Verify Deployment

Connect to EKS:

```bash
aws eks update-kubeconfig \
  --region ap-south-1 \
  --name devsecops-eks-cluster
```

Check namespaces:

```bash
kubectl get namespaces
```

Check dev deployment:

```bash
kubectl get all -n dev
```

Check staging deployment:

```bash
kubectl get all -n staging
```

Check production deployment:

```bash
kubectl get all -n production
```

Check production service URL:

```bash
kubectl get svc devsecops-service -n production
```

Open the LoadBalancer URL in a browser:

```text
http://<EXTERNAL-IP>
```

---

## Useful Verification Commands

Check pod status:

```bash
kubectl get pods -n dev
kubectl get pods -n staging
kubectl get pods -n production
```

Check rollout status:

```bash
kubectl rollout status deployment/devsecops-app -n dev
kubectl rollout status deployment/devsecops-app -n staging
kubectl rollout status deployment/devsecops-app -n production
```

Check deployed image:

```bash
kubectl get deployment devsecops-app -n production \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

Check production service:

```bash
kubectl describe svc devsecops-service -n production
```

---

## Artifacts

The workflow uploads artifacts such as:

```text
raw-json-security-reports-<run_id>
individual-excel-security-reports-<run_id>
```

The Excel artifact contains individual reports for each scan.

---

## Troubleshooting

### Deployment job skipped

Check:

```text
container_build_ok
policy_failed
manual_approval
deploy_environment
```

Deployment runs only when:

```text
container_build_ok = true
AND deploy_environment != skip-deployment
AND policy passed OR manual approval completed
```

### Docker image is empty

Make sure `dockerfile_first_build.sh` exports image and port to GitHub environment:

```bash
echo "IMAGE=$IMAGE" >> "$GITHUB_ENV"
echo "APP_PORT=$EXPOSED_PORT" >> "$GITHUB_ENV"
```

### Kubernetes service validation error

Make sure `k8s/service.yaml` starts with:

```yaml
apiVersion: v1
kind: Service
```

### LoadBalancer URL pending

Wait 1–2 minutes and check again:

```bash
kubectl get svc devsecops-service -n production
```

---

## Cleanup

After testing or demo, delete the namespaces:

```bash
kubectl delete namespace dev
kubectl delete namespace staging
kubectl delete namespace production
```

Delete the EKS cluster to avoid AWS charges:

```bash
eksctl delete cluster \
  --name devsecops-eks-cluster \
  --region ap-south-1
```

Verify deletion:

```bash
aws eks list-clusters --region ap-south-1
```

Expected:

```json
{
  "clusters": []
}
```

---

## Technology Stack

| Category | Tools |
|---|---|
| CI/CD | GitHub Actions |
| Cloud | AWS |
| Deployment | Amazon EKS |
| Containerization | Docker |
| Registry | Docker Hub |
| Secret scanning | GitLeaks |
| SAST | SonarCloud |
| Dependency scanning | npm audit, Safety, Snyk |
| Container scanning | Trivy |
| IaC scanning | Checkov |
| Policy-as-Code | OPA/Rego |
| Reporting | Python, OpenPyXL |
| Email alerts | SendGrid |
| Orchestration | Kubernetes |

---

## Final Summary

This project demonstrates a complete DevSecOps CI/CD pipeline.

It performs security scanning, generates individual Excel reports, applies OPA policy checks, sends alert emails, waits for manual approval, builds a Docker image using the customer Dockerfile, pushes the image to Docker Hub, and deploys the application to Amazon EKS across dev, staging, and production namespaces.

The project shows how security, compliance, reporting, approval, and deployment can be integrated into one automated software delivery pipeline.
