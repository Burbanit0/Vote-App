# Local reproduction of the GitHub "Backend CI" job (.github/workflows/backend-ci-cd-pipeline.yml).
#
# Fidelity choices:
#  - python:3.11 == actions/setup-python python-version '3.11' (exact interpreter).
#    Base distro is Debian (slim) rather than Ubuntu; irrelevant for pure-Python +
#    manylinux wheels, and it guarantees the same 3.11.x the runner uses.
#  - build-essential present so any sdist-only dep compiles (numpy/scipy ship wheels).
#  - Installs BOTH requirements.txt and requirements-dev.txt (== the CI install step).
#
# CI checks run as CMD, so `docker run` exits non-zero exactly when the PR would fail.
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install layer — cached unless the requirements files change.
COPY flask_voter_app/requirements.txt flask_voter_app/requirements-dev.txt flask_voter_app/
RUN pip install -r flask_voter_app/requirements.txt \
 && pip install -r flask_voter_app/requirements-dev.txt

# Source layer.
COPY flask_voter_app/ flask_voter_app/

# Mirror the workflow steps in order. flake8/bandit/pip-audit are non-blocking
# upstream (continue-on-error / --exit-zero); mypy + pytest(--cov-fail-under=30) gate.
ENV FLASK_ENV=testing JWT_SECRET_KEY=ci-test-secret
CMD ["bash","-euo","pipefail","-c","\
echo '=== Flake8 (non-blocking) ===';   flake8 --config=flask_voter_app/.flake8 flask_voter_app || echo '(flake8 failed — non-blocking)'; \
echo '=== Bandit (non-blocking) ===';   bandit -r flask_voter_app/api -ll --skip B104,B311 --exit-zero; \
echo '=== pip-audit (non-blocking) ==='; pip-audit --requirement flask_voter_app/requirements.txt || echo '(pip-audit failed — non-blocking)'; \
cd flask_voter_app; \
echo '=== Mypy (gating) ===';           python -m mypy api/ --config-file mypy.ini; \
echo '=== Pytest + coverage (gating) ==='; python -m pytest api/tests -v --cov=api --cov-report=term-missing --cov-report=xml --cov-fail-under=30; \
echo '=== Backend CI: PASS ==='"]
