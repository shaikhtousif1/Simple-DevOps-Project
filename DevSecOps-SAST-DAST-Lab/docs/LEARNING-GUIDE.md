# Learning Guide: Read the Findings, Then Fix Them

## SAST: Semgrep

SAST means Static Application Security Testing. The scanner inspects source code and matches potentially dangerous constructs without starting the web server.

In this lab:
- The SQL rule looks for an f-string passed to a database `execute()` call.
- The XSS rule flags dynamic content passed to `render_template_string()`.

These are intentionally simple syntax-pattern rules. Production-grade taint analysis follows data from a source (for example, an HTTP query parameter) to a sink (for example, a SQL execution function or HTML response) and uses framework-aware rules.

**Exercise:** change the SQL query to `connection.execute("SELECT id, name FROM products WHERE name = ?", (name,))`. Run Semgrep again. Add a test for a value containing a quote and verify it is treated as data, not SQL.

## DAST: OWASP ZAP

DAST means Dynamic Application Security Testing. ZAP interacts with the running service over HTTP. It can discover routes, inspect response headers/cookies, and test for common web weaknesses.

- Baseline scan: primarily passive checks; useful for a quick CI signal.
- Full scan: includes active rules that send attack-like requests. Use only on an explicitly authorized, isolated target.
- Alert: a scanner observation requiring triage, not automatically proof of exploitability.
- False positive: a finding that does not represent a vulnerability in the tested context.
- False negative: a vulnerability the scanner did not detect.

**Exercise:** download the ZAP HTML artifact from a workflow run. For every alert, record URL, parameter, risk, confidence, evidence, remediation and whether you reproduced it safely.

## SCA: Trivy

Software Composition Analysis identifies known vulnerabilities in dependencies and base images. A CVE finding should be evaluated using package version, fixed version, severity, exploitability/reachability, and whether the vulnerable component is present in the shipped artifact.

**Exercise:** compare the filesystem scan and image scan. Explain why their results can differ.

## Secrets: Gitleaks

Secrets scanning detects patterns that resemble credentials. It does not revoke a leaked key, and a clean current tree does not guarantee that a secret never existed in Git history.

**Exercise:** use a fake canary string in a disposable branch. Observe the finding, remove the test value, and understand why a real exposed key must be rotated.

## CI policy design

Start in report-only mode while tuning rules. Then define:
1. Which severities block merge or release.
2. Which findings need human triage.
3. How exceptions are approved, scoped and expired.
4. Who owns remediation and the remediation SLA.
5. How reports are retained and reviewed.

Do not set every scanner to fail on every informational finding. Equally, do not suppress a genuine exploitable finding merely to get a green pipeline.
