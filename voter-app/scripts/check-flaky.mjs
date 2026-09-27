#!/usr/bin/env node
/**
 * check-flaky.mjs — fail the run if any e2e test only passed on a retry.
 *
 * playwright.config.ts sets `retries: 1` in CI, which is right for genuine
 * infrastructure hiccups and wrong for everything else: a test that fails then
 * passes is reported GREEN, so a selector rotting or a race creeping in stays
 * invisible until the suite is unusable. That is how the previous suite died.
 *
 * Playwright marks those tests `status: "flaky"` in the JSON report. This walks
 * the report and exits 1 if there are any, naming them.
 *
 * Usage: node scripts/check-flaky.mjs [path/to/results.json]
 */
import { readFileSync, existsSync } from 'node:fs';

const reportPath = process.argv[2] ?? 'playwright-report/results.json';

if (!existsSync(reportPath)) {
  // The suite crashed before writing a report (backend down, browsers missing…).
  // That failure is already loud on its own — don't add a confusing second one.
  console.warn(`[check-flaky] no report at ${reportPath} — skipping.`);
  process.exit(0);
}

const report = JSON.parse(readFileSync(reportPath, 'utf8'));
const flaky = [];

const walk = (suite, trail) => {
  const here = suite.title ? [...trail, suite.title] : trail;
  for (const spec of suite.specs ?? []) {
    for (const test of spec.tests ?? []) {
      if (test.status === 'flaky') {
        const attempts = (test.results ?? []).map((r) => r.status).join(' → ');
        flaky.push(`${[...here, spec.title].join(' › ')}  (${attempts})`);
      }
    }
  }
  for (const child of suite.suites ?? []) walk(child, here);
};

for (const suite of report.suites ?? []) walk(suite, []);

if (flaky.length === 0) {
  console.log('✅ No flaky test — every test passed on its first attempt.');
  process.exit(0);
}

console.error(`\n🔴 ${flaky.length} flaky test(s) — passed only on retry:\n`);
for (const line of flaky) console.error(`   • ${line}`);
console.error(
  '\n   A flaky test is a broken test: it protects nothing and it trains everyone\n' +
    '   to re-run instead of to look. Fix the race (or the selector) rather than\n' +
    '   the symptom. The HTML report has the trace of the failed attempt.\n'
);
process.exit(1);
