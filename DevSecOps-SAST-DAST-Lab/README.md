# DevSecOps Lab: SAST, DAST, SCA and Secrets Scanning

A hands-on, intentionally vulnerable Flask application used to learn how application-security checks fit into a CI pipeline. The lab is isolated under this folder so it does not disturb the existing Ansible, Docker, Jenkins or Kubernetes examples in the repository.

> **Safety:** This application intentionally contains SQL injection and reflected-XSS examples. It is for local training only. Docker Compose binds it to `127.0.0.1`; do not expose it to the internet, deploy it to a shared cluster, or use it against systems you do not own.

## What you will learn

| Control | Tool | What it checks | Where |
|---|---|---|---|
| SAST | Semgrep | Source-code patterns and insecure coding practices | `app/` |
| Secrets detection | Gitleaks | Credentials accidentally committed to Git | Entire repository |
| SCA / filesystem scan | Trivy | Vulnerable OS and application dependencies, plus misconfigurations | Filesystem |
| Container image scan | Trivy | Vulnerabilities in the built image | Docker image |
| DAST | OWASP ZAP | The running application's externally observable behavior | Local container on port 5000 |
| Tests | pytest | Basic application behavior | `tests/` |

**SAST vs DAST:** SAST analyzes source code without running the application. DAST sends HTTP requests to a running application and observes responses. They find different classes of issues and should complement each other. Trivy dependency scanning is SCA, not SAST.

## Architecture

```text
Developer branch / Pull Request
             |
             v
       GitHub Actions
             |
      +------+-----------------------------+
      |                                    |
      v                                    v
  Build & tests                     Security checks
      |                             - Semgrep (SAST)
      |                             - Gitleaks (secrets)
      |                             - Trivy (SCA / config)
      |                                    |
      v                                    v
  Build Docker image                 Reports / gate results
      |
      v
  Trivy image scan
      |
      v
  Start app on runner localhost
      |
      v
  OWASP ZAP DAST scan
      |
      v
  Upload HTML / JSON reports
```

## 1. Run the application locally

Prerequisites: Docker Desktop with Compose v2, or Python 3.11+.

From this directory:

```bash
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:5000/health
```

Open http://127.0.0.1:5000 in your browser. Stop it with:

```bash
docker compose down
```

The application is deliberately vulnerable:
- `/search?q=...` inserts untrusted input into an HTML template (reflected XSS).
- `/lookup?name=...` builds a SQL statement using string interpolation (SQL injection).

Use only harmless lab inputs. The goal is to understand scanner findings and then fix the code—not to attack anything.

## 2. Run SAST with Semgrep

Install and run:

```bash
python -m pip install semgrep
semgrep scan --config .semgrep.yml --error app/
```

Study the finding:
1. Open the reported file and line.
2. Identify the source of untrusted input.
3. Follow how the value reaches a dangerous sink.
4. Fix the code using parameterized SQL and context-aware output escaping.
5. Run Semgrep again and confirm the finding is gone.

The custom rules in `.semgrep.yml` are intentionally small so you can understand how Semgrep matches syntax patterns. They are training rules, not a complete security policy.

## 3. Run secrets scanning with Gitleaks

Install Gitleaks using the official installation instructions, then run:

```bash
gitleaks detect --source . --redact --verbose
```

To understand the difference between a real secret and a false positive, use a disposable test repository or a throwaway branch. **Never commit a real credential to test the scanner.** If a real secret is exposed, revoke/rotate it; deleting the line is not enough.

## 4. Run SCA and configuration scanning with Trivy

Install Trivy, then run:

```bash
trivy fs --scanners vuln,misconfig,secret .
```

SCA (Software Composition Analysis) examines third-party packages and their known vulnerabilities. The filesystem scan can also inspect supported configuration files. Review package name, installed version, fixed version, severity and reachability before deciding remediation.

Build and scan the image:

```bash
docker build -t devsecops-lab:local .
trivy image --severity HIGH,CRITICAL devsecops-lab:local
```

## 5. Run DAST with OWASP ZAP

Start the app first:

```bash
docker compose up --build -d
```

Then run ZAP's baseline scan from its container:

```bash
docker run --rm --network host \
  -v "$PWD:/zap/wrk:rw" \
  ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t http://127.0.0.1:5000 \
  -J zap-report.json -r zap-report.html
```

The baseline scan is primarily passive: it crawls and inspects responses without performing the more intrusive active attack rules. The GitHub Actions workflow uses ZAP's full scan against this isolated lab app to demonstrate active DAST. Never point active scanning at a production or third-party target without explicit authorization.

## 6. Understand the GitHub Actions pipeline

Workflow: `.github/workflows/security-pipeline.yml`

It runs on pushes and pull requests that touch this lab:
- **test** installs dependencies and runs pytest.
- **sast-and-supply-chain** runs Semgrep, Gitleaks and Trivy filesystem scanning.
- **container-scan** builds the image and scans it with Trivy.
- **dast** starts the app on the GitHub-hosted runner and runs OWASP ZAP against localhost. Reports are uploaded even when the scan reports findings.

Because this is an intentionally vulnerable training app, security jobs may fail. That is expected: inspect the logs and reports, remediate one issue at a time, and rerun. Do not weaken or suppress a rule just to make the badge green.

## 7. Suggested learning exercises

1. Run Semgrep locally. Explain each finding in your own words.
2. Replace the unsafe SQL construction with a parameterized query. Add a regression test.
3. Replace dynamic HTML string construction with a normal template and escaped variables. Add a test.
4. Compare Semgrep output before and after each fix.
5. Run ZAP baseline, inspect the HTML report, and map each alert to an HTTP response/header.
6. Compare ZAP passive baseline results with the full active scan in CI.
7. Add a vulnerable dependency in a disposable branch, run Trivy, then upgrade to a fixed version.
8. Add a fake canary credential only in a disposable local test fixture (never a real credential), observe Gitleaks, and remove it.
9. Change the workflow so HIGH/CRITICAL findings block a release while lower-severity findings are reported for triage.
10. Add SARIF upload for supported scanners and review findings in GitHub Security.

## 8. Recommended remediation order

- Fix exploitable code defects first (SQL injection and XSS).
- Upgrade vulnerable direct/transitive dependencies after checking compatibility.
- Remove secrets from history where necessary and rotate exposed credentials.
- Add secure response headers, input validation and least-privilege runtime settings.
- Re-run unit tests, SAST, SCA, container scanning and DAST after every meaningful fix.

## References

- [Semgrep documentation](https://semgrep.dev/docs/)
- [Gitleaks](https://github.com/gitleaks/gitleaks)
- [Trivy documentation](https://trivy.dev/latest/)
- [OWASP ZAP documentation](https://www.zaproxy.org/docs/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

## Lab status

This is a learning scaffold, not a production-ready application or a production security policy. Pin action versions, review scanner updates, tune rules to your stack, and establish severity/exception governance before adopting the pattern in a real delivery pipeline.
