# syntax=docker/dockerfile:1
# Local CI mirror — Security Audit job. Bundles the SAST/secret/CVE scanners that
# aren't in the lint/type/test pipelines (Semgrep, Gitleaks, Trivy) into one image,
# the same way frontend/backend.Dockerfile bundle their checks. Mirrors
# .github/workflows/audit.yml so failures surface locally before a push.
FROM python:3.11-slim

ARG GITLEAKS_VERSION=8.18.4
ARG TRIVY_VERSION=0.71.2

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl git ca-certificates tar bash \
 && rm -rf /var/lib/apt/lists/*

# Semgrep (multi-language SAST) via pip.
RUN pip install --no-cache-dir semgrep

# Gitleaks (secret scanning) — pinned release tarball.
RUN curl -sSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
      | tar -xz -C /usr/local/bin gitleaks \
 && gitleaks version

# Trivy (deps / containers / misconfig) — pinned release tarball.
RUN curl -sSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
      | tar -xz -C /usr/local/bin trivy \
 && trivy --version

WORKDIR /repo
# COPY the working tree (incl. .git so Gitleaks can scan history). The repo-root
# .semgrepignore + ci-local/audit.Dockerfile.dockerignore keep the context lean.
COPY . .

# Gitleaks BLOCKS on secrets; Semgrep + Trivy are informational (printed, non-gating)
# — same posture as the GitHub workflow.
CMD ["bash", "ci-local/audit-ci.sh"]
