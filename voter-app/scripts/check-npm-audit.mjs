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
 * time-boxed exception in .github/npm-audit-allowlist.json (same spirit as
 * .github/ci-health-snoozes.json):
 *
 *   "GHSA-xxxx-xxxx-xxxx": {
 *     "until": "YYYY-MM-DD",            // at most MAX_HORIZON_DAYS ahead
 *     "reason": "why it's acceptable until then",
 *     "nodes": ["node_modules/eslint/node_modules/brace-expansion"]  // the reviewed install paths
 *   }
 *
 * The exception covers exactly the reviewed `nodes`: if the advisory later shows
 * up at another install path (say, pulled in by a shipped dependency), the gate
 * fails again, because the reason that was reviewed no longer describes it.
 *
 * Exits 1 when: an advisory is not covered; an entry is malformed, expired (and
 * still needed) or too far ahead; or the audit could not run — an audit that
 * didn't happen never counts as clean. The audit is forced to the full tree and
 * online, whatever NODE_ENV or npm config says.
 *
 * Usage (from voter-app/): npm run audit:gate [-- --report saved-audit.json]
 *   --report      read a saved `npm audit --json` output instead of running npm
 *   --allowlist   allowlist path (default: ../.github/npm-audit-allowlist.json)
 *   --today       YYYY-MM-DD override, for tests
 * Tests: node --test scripts/*.test.mjs
 */
import { readFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { parseArgs } from 'node:util';

const here = dirname(fileURLToPath(import.meta.url));
const GATED = new Set(['high', 'critical']);
export const MAX_HORIZON_DAYS = 90;

class GateError extends Error {}
const fail = (msg) => {
  throw new GateError(msg);
};

const tail = (s, n = 800) => String(s ?? '').slice(-n);

export function runAudit() {
  // npm_execpath is the npm CLI that launched `npm run audit:gate`: running it
  // through this same node binary avoids resolving `npm` from PATH.
  const npmCli = process.env.npm_execpath;
  if (!npmCli) fail('run this through `npm run audit:gate` (or pass --report <file>).');
  // Explicit flags beat NODE_ENV=production (implies omit=dev) and offline=true
  // in a user's npmrc, both of which return a well-formed, falsely clean report.
  const env = { ...process.env };
  delete env.NODE_ENV;
  const res = spawnSync(
    process.execPath,
    [
      npmCli,
      'audit',
      '--json',
      '--include=dev',
      '--include=optional',
      '--include=peer',
      '--offline=false',
    ],
    { cwd: resolve(here, '..'), encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, env }
  );
  if (res.error) fail(`npm audit could not run: ${res.error.message}\n${tail(res.stderr)}`);
  return { raw: res.stdout, stderr: res.stderr };
}

export function parseReport(raw, stderr = '') {
  let report;
  try {
    report = JSON.parse(raw);
  } catch {
    fail(
      `npm audit produced no JSON report — treating as a failed audit, not a clean one.\n${tail(raw, 500)}\n${tail(stderr)}`
    );
  }
  if (!report?.metadata?.vulnerabilities || typeof report.vulnerabilities !== 'object') {
    fail(
      `npm audit did not complete (no vulnerability metadata) — treating as a failed audit, not a clean one.\n${tail(JSON.stringify(report), 500)}\n${tail(stderr)}`
    );
  }
  return report;
}

/** Strict YYYY-MM-DD: a real calendar date, not just the right shape. */
export function isValidDate(s) {
  if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const d = new Date(`${s}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

export function addDays(day, n) {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export function loadAllowlist(path) {
  if (!existsSync(path)) return {};
  let entries;
  try {
    entries = JSON.parse(readFileSync(path, 'utf8'));
  } catch (e) {
    fail(`${path} is not valid JSON: ${e.message}`);
  }
  if (!entries || typeof entries !== 'object' || Array.isArray(entries)) {
    fail(`${path} must be a JSON object`);
  }
  return Object.fromEntries(Object.entries(entries).filter(([id]) => !id.startsWith('_')));
}

/** One record per gated advisory: id -> { severity, title, url, nodes }. */
export function gatedAdvisories(report) {
  const found = new Map();
  for (const vuln of Object.values(report.vulnerabilities)) {
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
        nodes: new Set(),
      };
      for (const node of vuln.nodes ?? []) rec.nodes.add(node);
      found.set(id, rec);
    }
  }
  return found;
}

function entryProblems(id, entry, today, horizon) {
  const problems = [];
  if (!isValidDate(entry?.until)) problems.push(`${id}: "until" must be a real YYYY-MM-DD date`);
  else if (entry.until < today) {
    problems.push(
      `${id}: exception expired on ${entry.until} — fix the dependency, or renew it in a reviewed PR`
    );
  } else if (entry.until > horizon) {
    problems.push(
      `${id}: "until" ${entry.until} is more than ${MAX_HORIZON_DAYS} days ahead (max ${horizon})`
    );
  }
  if (typeof entry?.reason !== 'string' || !entry.reason.trim()) {
    problems.push(`${id}: missing "reason"`);
  }
  if (!Array.isArray(entry?.nodes) || entry.nodes.length === 0) {
    problems.push(`${id}: missing "nodes" (the reviewed install paths, from \`npm audit --json\`)`);
  }
  return problems;
}

/** Pure decision: what blocks, what is waived, what to clean up. */
export function evaluate(advisories, allowlist, today) {
  const horizon = addDays(today, MAX_HORIZON_DAYS);
  const problems = [];
  const blocking = [];
  const waived = [];
  // An entry whose advisory is gone never fails, even expired: the PR that
  // fixed the dependency should delete it, and an expiry date on a dead entry
  // must not turn unrelated PRs red.
  const unused = Object.keys(allowlist).filter((id) => !advisories.has(id));

  for (const [id, rec] of advisories) {
    const nodes = [...rec.nodes].sort();
    const where = nodes.join(', ') || '(no install path reported)';
    const line = `${id} (${rec.severity}) ${rec.title} — ${rec.url}\n      at ${where}`;
    const entry = allowlist[id];
    if (!entry) {
      blocking.push(line);
      continue;
    }
    problems.push(...entryProblems(id, entry, today, horizon));
    const reviewed = new Set(Array.isArray(entry.nodes) ? entry.nodes : []);
    const unreviewed = nodes.filter((n) => !reviewed.has(n));
    if (unreviewed.length) {
      blocking.push(`${line}\n      not covered by the exception: ${unreviewed.join(', ')}`);
    } else {
      waived.push(line);
    }
  }
  return { problems, blocking, waived, unused };
}

export function main(argv = process.argv.slice(2)) {
  let values;
  try {
    ({ values } = parseArgs({
      args: argv,
      options: {
        report: { type: 'string' },
        allowlist: { type: 'string' },
        today: { type: 'string' },
      },
    }));
  } catch (e) {
    fail(e.message);
  }
  const today = values.today ?? new Date().toISOString().slice(0, 10);
  if (!isValidDate(today)) fail(`--today must be YYYY-MM-DD, got ${values.today}`);
  const allowlistPath = values.allowlist ?? resolve(here, '../../.github/npm-audit-allowlist.json');

  const { raw, stderr } = values.report
    ? { raw: readFileSync(values.report, 'utf8'), stderr: '' }
    : runAudit();
  const report = parseReport(raw, stderr);
  const allowlist = loadAllowlist(allowlistPath);
  const { problems, blocking, waived, unused } = evaluate(
    gatedAdvisories(report),
    allowlist,
    today
  );

  if (waived.length) {
    console.log(
      `[npm-audit] covered by an exception (.github/npm-audit-allowlist.json):\n  ${waived.join('\n  ')}`
    );
  }
  if (unused.length) {
    console.log(`[npm-audit] exceptions no longer needed — delete them: ${unused.join(', ')}`);
  }
  if (problems.length) console.error(`[npm-audit] allowlist problems:\n  ${problems.join('\n  ')}`);
  if (blocking.length) {
    console.error(
      `[npm-audit] ${blocking.length} high/critical advisory(ies) not covered:\n  ${blocking.join('\n  ')}\n` +
        "Fix: `npm audit fix --package-lock-only` with npm >= 11.10 (so .npmrc's min-release-age is honoured). " +
        'If no fixed version is usable yet, add an entry (until, reason, nodes) to .github/npm-audit-allowlist.json in a reviewed PR.'
    );
  }
  if (problems.length || blocking.length) return 1;
  if (waived.length) {
    console.log(
      `[npm-audit] OK — ${waived.length} high/critical advisory(ies), all covered by exceptions.`
    );
  } else {
    console.log('[npm-audit] OK — no high/critical advisories.');
  }
  return 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    process.exitCode = main();
  } catch (e) {
    if (!(e instanceof GateError)) throw e;
    console.error(`[npm-audit] ${e.message}`);
    process.exitCode = 1;
  }
}
