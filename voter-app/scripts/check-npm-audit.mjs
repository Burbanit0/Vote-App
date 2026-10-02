#!/usr/bin/env node
/**
 * check-npm-audit.mjs — the npm advisory gate: full dependency tree, high and
 * critical, minus a reviewed allowlist of advisories that each expire.
 *
 * Why not plain `npm audit --audit-level=high`: that made a required check fail
 * on advisory-database updates rather than on the diff. On 2026-09-30 a new
 * brace-expansion advisory (reachable only through eslint) turned polity red on
 * push, and every frontend PR with it, with zero code change — and the only way
 * out was to weaken the gate.
 *
 * Why not `--omit=dev` instead: devDependencies do ship here. workbox-window is
 * loaded into the client bundle through vite-plugin-pwa's virtual module, and
 * the workbox-* runtime is built into the generated service worker; both are
 * `dev: true` in the lockfile.
 *
 * So the whole tree stays gated, and an advisory with no usable fix yet gets a
 * reviewed, time-boxed exception in .github/npm-audit-allowlist.json — same
 * shape and spirit as .github/ci-health-snoozes.json:
 *
 *   { "GHSA-xxxx-xxxx-xxxx": { "until": "YYYY-MM-DD", "reason": "why it's acceptable for now" } }
 *
 * Exits 1 when: an unlisted high/critical advisory is present; an allowlist
 * entry has expired, or lacks a date or a reason; or the audit itself could not
 * run (registry down, bad JSON) — an audit that didn't happen never counts as
 * clean.
 *
 * Usage (from voter-app/): npm run audit:gate [-- --report audit.json]
 *   --report reads a saved `npm audit --json` output instead of running npm.
 */
import { readFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const allowlistPath = resolve(here, '../../.github/npm-audit-allowlist.json');
const GATED = new Set(['high', 'critical']);

const fail = (msg) => {
  console.error(`[npm-audit] ${msg}`);
  process.exit(1);
};

function loadReport() {
  const i = process.argv.indexOf('--report');
  let raw;
  if (i !== -1) {
    raw = readFileSync(process.argv[i + 1], 'utf8');
  } else {
    // npm audit exits non-zero whenever it finds anything, so its status says
    // nothing about whether it ran; the JSON shape below is what's checked.
    // npm_execpath is the npm CLI that launched `npm run audit:gate`: running it
    // through this same node binary avoids resolving `npm` from PATH.
    const npmCli = process.env.npm_execpath;
    if (!npmCli) fail('run this through `npm run audit:gate` (or pass --report <file>).');
    const res = spawnSync(process.execPath, [npmCli, 'audit', '--json'], {
      cwd: resolve(here, '..'),
      encoding: 'utf8',
      maxBuffer: 64 * 1024 * 1024,
    });
    raw = res.stdout;
  }
  let report;
  try {
    report = JSON.parse(raw);
  } catch {
    fail(
      `npm audit produced no JSON report — treating as a failed audit, not a clean one.\n${String(raw).slice(0, 500)}`
    );
  }
  if (!report?.metadata?.vulnerabilities || typeof report.vulnerabilities !== 'object') {
    fail(
      `npm audit did not complete (no vulnerability metadata) — treating as a failed audit, not a clean one.\n${JSON.stringify(report).slice(0, 500)}`
    );
  }
  return report;
}

function loadAllowlist(today) {
  if (!existsSync(allowlistPath)) return { entries: {}, problems: [] };
  const entries = JSON.parse(readFileSync(allowlistPath, 'utf8'));
  const problems = [];
  for (const [id, entry] of Object.entries(entries)) {
    if (id.startsWith('_')) continue; // _comment keys
    if (!/^\d{4}-\d{2}-\d{2}$/.test(entry?.until ?? ''))
      problems.push(`${id}: missing or malformed "until" (YYYY-MM-DD)`);
    else if (entry.until < today)
      problems.push(
        `${id}: allowlist entry expired on ${entry.until} — fix the dependency, or renew it in a reviewed PR with a fresh reason`
      );
    if (!entry?.reason?.trim()) problems.push(`${id}: missing "reason"`);
  }
  return { entries, problems };
}

/** One record per gated advisory: id -> { severity, title, url, packages }. */
function gatedAdvisories(report) {
  const found = new Map();
  for (const [pkg, vuln] of Object.entries(report.vulnerabilities)) {
    for (const via of vuln.via ?? []) {
      // String entries point at another package's advisory (transitive);
      // that package carries the advisory object itself, so it's counted there.
      if (typeof via !== 'object' || !GATED.has(via.severity)) continue;
      const id =
        String(via.url ?? '')
          .split('/')
          .pop() || `npm-${via.source}`;
      const rec = found.get(id) ?? {
        severity: via.severity,
        title: via.title,
        url: via.url,
        packages: new Set(),
      };
      rec.packages.add(pkg);
      found.set(id, rec);
    }
  }
  return found;
}

const today = new Date().toISOString().slice(0, 10);
const report = loadReport();
const { entries, problems } = loadAllowlist(today);
const advisories = gatedAdvisories(report);

const blocking = [];
const waived = [];
for (const [id, rec] of advisories) {
  const line = `${id} (${rec.severity}) ${rec.title} — ${[...rec.packages].join(', ')} — ${rec.url}`;
  (entries[id] ? waived : blocking).push(line);
}
const unused = Object.keys(entries).filter((id) => !id.startsWith('_') && !advisories.has(id));

if (waived.length)
  console.log(
    `[npm-audit] allowlisted (see .github/npm-audit-allowlist.json):\n  ${waived.join('\n  ')}`
  );
if (unused.length)
  console.log(`[npm-audit] allowlist entries no longer needed — remove them: ${unused.join(', ')}`);
if (problems.length) console.error(`[npm-audit] allowlist problems:\n  ${problems.join('\n  ')}`);
if (blocking.length) {
  console.error(
    `[npm-audit] ${blocking.length} high/critical advisory(ies) not allowlisted:\n  ${blocking.join('\n  ')}\n` +
      "Fix: `npm audit fix --package-lock-only` with npm >= 11.10 (so .npmrc's min-release-age is honoured). " +
      'If no fixed version is usable yet, add a dated entry with a reason to .github/npm-audit-allowlist.json in a reviewed PR.'
  );
}
if (problems.length || blocking.length) process.exit(1);
if (advisories.size === 0) console.log('[npm-audit] OK — no high/critical advisories.');
else
  console.log(`[npm-audit] OK — ${advisories.size} high/critical advisory(ies), all allowlisted.`);
