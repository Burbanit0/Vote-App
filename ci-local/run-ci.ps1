<#
.SYNOPSIS
  Run the GitHub CI jobs locally in a faithful Docker mirror (Ubuntu 24.04 / Node 20
  for the frontend, Python 3.11 for the backend) before opening a PR.

.DESCRIPTION
  Builds and runs ci-local/frontend.Dockerfile and/or backend.Dockerfile from the
  repo root. The CI checks run as the container CMD, so a non-zero exit means the
  PR would fail. Prints a PASS/FAIL summary and exits non-zero if any target failed.

.PARAMETER Target
  frontend | backend | e2e | audit | code | all  (default: all)
    all   = frontend + backend + e2e + audit (run before each push)
    code  = frontend + backend (quick iteration, skips e2e and the audit)
    e2e   = Playwright suite, backend fixture included (~6 min, gating since PR #170)
    audit = security scanners only (Semgrep / Gitleaks / Trivy)

.PARAMETER NoCache
  Force a clean rebuild (no Docker layer cache).

.EXAMPLE
  ./ci-local/run-ci.ps1                 # frontend + backend + e2e + audit
  ./ci-local/run-ci.ps1 -Target code    # skip e2e and the audit for quick iteration
  ./ci-local/run-ci.ps1 -Target e2e     # Playwright only
  ./ci-local/run-ci.ps1 -Target audit   # security scan only
  ./ci-local/run-ci.ps1 -NoCache
#>
[CmdletBinding()]
param(
  [ValidateSet('frontend','backend','e2e','audit','code','all')]
  [string]$Target = 'all',
  [switch]$NoCache
)

$ErrorActionPreference = 'Continue'
$env:DOCKER_BUILDKIT = '1'

# Always operate from the repo root (this script's parent), so the build context
# is the repo regardless of where the user invokes it from.
$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepoRoot

# ── Preflight: tracked-content guard ─────────────────────────────────────────
# The images COPY the working tree, but GitHub checks out only git-TRACKED files.
# A source file on disk that git doesn't track (untracked OR gitignored) is absent
# on CI → "passes locally, fails on PR". This is the exact bug that cost a day:
# src/lib/utils.ts was swept up by a broad `lib/` .gitignore pattern. Fail loudly.
$stray = (git status --porcelain --ignored -- voter-app/src fast_api_voter/api 2>$null) |
  Where-Object { $_ -match '^(\?\?|!!)' -and $_ -match '\.(ts|tsx|js|jsx|py)$' -and $_ -notmatch '__pycache__|\.pyc' }
if ($stray) {
  Write-Host "ERROR: source files exist on disk but are NOT tracked by git (absent on CI):" -ForegroundColor Red
  $stray | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
  Write-Host "Commit them (or fix .gitignore) before validating — CI will not see them." -ForegroundColor Red
  Pop-Location
  exit 1
}

$cacheArg = $null
if ($NoCache) { $cacheArg = '--no-cache' }
$results = [ordered]@{}

function Invoke-CiJob([string]$Name, [string]$Dockerfile, [string]$Tag) {
  Write-Host "`n========== $Name : build ==========" -ForegroundColor Cyan
  $buildArgs = @('build','-f',$Dockerfile,'-t',$Tag)
  if ($cacheArg) { $buildArgs += $cacheArg }
  $buildArgs += '.'
  & docker @buildArgs
  if ($LASTEXITCODE -ne 0) { $script:results[$Name] = 'BUILD FAILED'; return }

  Write-Host "`n========== $Name : run (CI checks) ==========" -ForegroundColor Cyan
  & docker run --rm --cpus=4 $Tag
  if ($LASTEXITCODE -eq 0) { $script:results[$Name] = 'PASS' } else { $script:results[$Name] = 'FAIL' }
}

try {
  if ($Target -in 'frontend','code','all') { Invoke-CiJob 'Frontend CI' 'ci-local/frontend.Dockerfile' 'vote-ci-frontend' }
  if ($Target -in 'backend','code','all')  { Invoke-CiJob 'Backend CI'  'ci-local/backend.Dockerfile'  'vote-ci-backend' }
  if ($Target -in 'e2e','all')             { Invoke-CiJob 'Playwright E2E' 'ci-local/e2e.Dockerfile' 'vote-ci-e2e' }
  if ($Target -in 'audit','all')           { Invoke-CiJob 'Security Audit' 'ci-local/audit.Dockerfile' 'vote-ci-audit' }
}
finally {
  Pop-Location
}

Write-Host "`n==================== SUMMARY ====================" -ForegroundColor Yellow
$failed = $false
foreach ($k in $results.Keys) {
  $v = $results[$k]
  $color = 'Red'; if ($v -eq 'PASS') { $color = 'Green' }
  if ($v -ne 'PASS') { $failed = $true }
  Write-Host ("{0,-14} {1}" -f $k, $v) -ForegroundColor $color
}
Write-Host "================================================" -ForegroundColor Yellow

if ($failed) { exit 1 } else { exit 0 }
