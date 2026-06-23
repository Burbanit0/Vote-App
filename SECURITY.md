# Security Policy

## Context

Vote Lab is a **personal voting-theory research and education project**. It has
**no real users and stores no real personal data** — every "electorate" is
synthetic and generated on the fly. Security and performance are deliberately
secondary to the rigour of the voting algorithms and the clarity of the
visualisations. Please keep that scope in mind when assessing impact.

## Reporting a vulnerability

Please report security issues **privately** — do not open a public issue.

- Preferred: GitHub **"Report a vulnerability"** (Security → Advisories →
  *Report a vulnerability*), which opens a private advisory thread.
- Alternative: email the maintainer at **gaultier.burban@gmail.com**.

Include enough to reproduce: affected component (backend `flask_voter_app/` or
frontend `voter-app/`), version/commit, steps, and impact. As a hobby project,
responses are best-effort — expect an acknowledgement within a week or two.

## Scope

In scope: authentication/JWT handling, the FastAPI endpoints, dependency CVEs,
and anything that could affect someone running this code locally.

Out of scope: findings that require an unrealistic deployment (the project ships
no production instance with real data), denial-of-service against your own local
instance, and the documented local-dev defaults (e.g. the `myuser/mypassword`
Postgres credentials in `docker-compose.yml`, which exist only for local use).

## Automated security tooling

This repository is continuously scanned (see `.github/workflows/audit.yml` and
`scripts/audit.sh`): **Semgrep** (SAST), **Gitleaks** (secrets), **Trivy**
(dependencies/containers/misconfig), **CodeQL** (code scanning), plus **bandit**,
**pip-audit** and **npm audit** in the CI pipelines. Semgrep findings, Trivy
HIGH/CRITICAL, and any detected secret fail the build.
