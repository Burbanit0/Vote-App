<#
.SYNOPSIS
  Run the GitHub CI jobs locally in a faithful Docker mirror (Ubuntu 24.04 / Node 20
  for the frontend, Python 3.11 for the backend) before opening a PR.

.DESCRIPTION
  Builds and runs ci-local/frontend.Dockerfile and/or backend.Dockerfile from the
  repo root. The CI checks run as the container CMD, so a non-zero exit means the
  PR would fail. Prints a PASS/FAIL summary and exits non-zero if any target failed.

.PARAMETER Target
  frontend | backend | all  (default: all)

.PARAMETER NoCache
  Force a clean rebuild (no Docker layer cache).

.EXAMPLE
  ./ci-local/run-ci.ps1                 # both jobs
  ./ci-local/run-ci.ps1 -Target frontend
  ./ci-local/run-ci.ps1 -NoCache
#>
[CmdletBinding()]
param(
  [ValidateSet('frontend','backend','all')]
  [string]$Target = 'all',
  [switch]$NoCache
)

$ErrorActionPreference = 'Stop'
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
$stray = (git status --porcelain --ignored -- voter-app/src flask_voter_app/api 2>$null) |
  Where-Object { $_ -match '^(\?\?|!!)' -and $_ -match '\.(ts|tsx|js|jsx|py)$' -and $_ -notmatch '__pycache__|\.pyc' }
if ($stray) {
  Write-Host "ERROR: source files exist on disk but are NOT tracked by git (absent on CI):" -ForegroundColor Red
  $stray | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
  Write-Host "Commit them (or fix .gitignore) before validating — CI will not see them." -ForegroundColor Red
  Pop-Location
  exit 1
}

$cacheArg = if ($NoCache) { '--no-cache' } else { $null }
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
  $script:results[$Name] = if ($LASTEXITCODE -eq 0) { 'PASS' } else { 'FAIL' }
}

try {
  if ($Target -in 'frontend','all') { Invoke-CiJob 'Frontend CI' 'ci-local/frontend.Dockerfile' 'vote-ci-frontend' }
  if ($Target -in 'backend','all')  { Invoke-CiJob 'Backend CI'  'ci-local/backend.Dockerfile'  'vote-ci-backend' }
}
finally {
  Pop-Location
}

Write-Host "`n==================== SUMMARY ====================" -ForegroundColor Yellow
$failed = $false
foreach ($k in $results.Keys) {
  $v = $results[$k]
  $color = if ($v -eq 'PASS') { 'Green' } else { 'Red'; }
  if ($v -ne 'PASS') { $failed = $true }
  Write-Host ("{0,-14} {1}" -f $k, $v) -ForegroundColor $color
}
Write-Host "================================================" -ForegroundColor Yellow

if ($failed) { exit 1 } else { exit 0 }
