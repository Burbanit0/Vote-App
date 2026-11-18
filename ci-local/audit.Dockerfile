# syntax=docker/dockerfile:1
# Local CI mirror — Security Audit job. Bundles the SAST/secret/CVE scanners that
# aren't in the lint/type/test pipelines (Semgrep, Gitleaks, Trivy) into one image,
# the same way frontend/backend.Dockerfile bundle their checks. Mirrors
# .github/workflows/audit.yml so failures surface locally before a push.
FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f

ARG GITLEAKS_VERSION=8.18.4
ARG GITLEAKS_SHA256=ba6dbb656933921c775ee5a2d1c13a91046e7952e9d919f9bac4cec61d628e7d
ARG TRIVY_VERSION=0.71.2
ARG TRIVY_SHA256=0510e71e2fd39bf863856d499c8dc19feb4e7336546394c502a8f5cc7ab27460

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl git ca-certificates tar bash \
 && rm -rf /var/lib/apt/lists/*

# Semgrep (multi-language SAST) via pip.
# Same version as audit.yml's Semgrep SAST job: ci-local mirrors CI.
RUN pip install --no-cache-dir semgrep==1.179.0

# Gitleaks (secret scanning) — pinned release tarball, checked against its SHA-256
# (from the release's gitleaks_<version>_checksums.txt). Bump both ARGs together.
RUN curl -fsSL -o /tmp/gitleaks.tgz "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
 && echo "${GITLEAKS_SHA256}  /tmp/gitleaks.tgz" | sha256sum -c - \
 && tar -xzf /tmp/gitleaks.tgz -C /usr/local/bin gitleaks \
 && rm /tmp/gitleaks.tgz \
 && gitleaks version

# Trivy (deps / containers / misconfig) — pinned release tarball, checked against its
# SHA-256 (from the release's trivy_<version>_checksums.txt). Bump both ARGs together.
RUN curl -fsSL -o /tmp/trivy.tgz "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
 && echo "${TRIVY_SHA256}  /tmp/trivy.tgz" | sha256sum -c - \
 && tar -xzf /tmp/trivy.tgz -C /usr/local/bin trivy \
 && rm /tmp/trivy.tgz \
 && trivy --version

WORKDIR /repo
# COPY the working tree (incl. .git so Gitleaks can scan history). The repo-root
# .semgrepignore + ci-local/audit.Dockerfile.dockerignore keep the context lean.
COPY . .

# Semgrep, Trivy and Gitleaks all GATE (see audit-ci.sh) — same posture as the
# GitHub workflow's required Semgrep/Trivy/Gitleaks jobs.
CMD ["bash", "ci-local/audit-ci.sh"]
