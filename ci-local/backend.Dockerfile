# Local reproduction of the GitHub "Backend CI" job (.github/workflows/backend-ci-cd-pipeline.yml).
#
# Fidelity choices:
#  - python:3.14 == astral-sh/setup-uv's python-version '3.14' (exact interpreter).
#    Base distro is Debian (slim) rather than Ubuntu; irrelevant for pure-Python +
#    manylinux wheels, and it guarantees the same 3.14.x the runner uses.
#  - build-essential present so any sdist-only dep compiles (numpy/scipy ship wheels).
#  - Installs BOTH requirements.txt and requirements-dev.txt (== the CI install step).
#
# CI checks run as CMD, so `docker run` exits non-zero exactly when the PR would fail.
FROM python:3.14-slim-bookworm

# uv (Lot 1, PLAN_SOLIDITE_TECHNIQUE.md) — matches the CI workflow, which uses
# astral-sh/setup-uv instead of pip.
COPY --from=ghcr.io/astral-sh/uv:0.12.11 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install layer — cached unless the requirements files change.
COPY fast_api_voter/requirements.txt fast_api_voter/requirements-dev.txt fast_api_voter/
RUN uv pip install --system -r fast_api_voter/requirements.txt \
 && uv pip install --system -r fast_api_voter/requirements-dev.txt

# Source layer.
COPY fast_api_voter/ fast_api_voter/

# Mirror the workflow steps in order (matches GitHub CI gating).
# ruff (replaces flake8, Lot 1) + bandit = GATING. pip-audit = informational
# (continue-on-error upstream).
ENV FLASK_ENV=testing
CMD ["bash","-euo","pipefail","-c","\
echo '=== Ruff (gating) ===';           ruff check fast_api_voter; \
echo '=== Import layering (gating) ==='; (cd fast_api_voter && lint-imports); \
echo '=== Bandit (gating) ===';         bandit -r fast_api_voter/api -ll --skip B104,B311; \
echo '=== pip-audit (non-blocking) ==='; pip-audit --requirement fast_api_voter/requirements.txt || echo '(pip-audit failed — non-blocking)'; \
cd fast_api_voter; \
echo '=== Mypy (gating) ===';           python -m mypy api/ --config-file mypy.ini; \
echo '=== Pytest + coverage (gating) ==='; python -m pytest api/tests -v --cov=api --cov-report=term-missing --cov-report=xml --cov-fail-under=85; \
echo '=== Engine perf ceilings (pytest-benchmark, gating) ==='; python -m pytest api/tests/test_engine_benchmarks.py -v -o addopts=''; \
echo '=== Backend CI: PASS ==='"]
