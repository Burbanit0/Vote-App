// node --test scripts/*.test.mjs — the npm advisory gate's decision rules, on fixture
// reports. Kept out of vitest (src/**) on purpose: this guards a CI script.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { evaluate, gatedAdvisories, isValidDate, main, parseReport } from './check-npm-audit.mjs';

const ESLINT_NODE = 'node_modules/eslint/node_modules/brace-expansion';
const report = (nodes = [ESLINT_NODE], severity = 'high') => ({
  metadata: { vulnerabilities: { high: 1, critical: 0 } },
  vulnerabilities: {
    'brace-expansion': {
      nodes,
      via: [
        {
          source: 1,
          title: 'DoS',
          url: 'https://github.com/advisories/GHSA-aaaa-bbbb-cccc',
          severity,
        },
      ],
    },
    eslint: { nodes: ['node_modules/eslint'], via: ['brace-expansion'] },
  },
});
const TODAY = '2026-10-02';
const ok = { until: '2026-11-01', reason: 'eslint only', nodes: [ESLINT_NODE] };
const run = (rep, allow) => evaluate(gatedAdvisories(rep), allow, TODAY);

test('an unlisted high advisory blocks; transitive string entries are not double counted', () => {
  const r = run(report(), {});
  assert.equal(r.blocking.length, 1);
  assert.match(r.blocking[0], /GHSA-aaaa-bbbb-cccc/);
});

test('moderate advisories never block', () => {
  assert.deepEqual(run(report([ESLINT_NODE], 'moderate'), {}).blocking, []);
});

test('a valid exception covering every reviewed node waives it', () => {
  const r = run(report(), { 'GHSA-aaaa-bbbb-cccc': ok });
  assert.deepEqual([r.blocking, r.problems], [[], []]);
  assert.equal(r.waived.length, 1);
});

test('the advisory showing up at a new install path blocks again', () => {
  const r = run(report([ESLINT_NODE, 'node_modules/brace-expansion']), {
    'GHSA-aaaa-bbbb-cccc': ok,
  });
  assert.match(r.blocking[0], /not covered by the exception: node_modules\/brace-expansion/);
});

test('expired, too-far, impossible dates and missing fields are problems', () => {
  const id = 'GHSA-aaaa-bbbb-cccc';
  assert.match(run(report(), { [id]: { ...ok, until: '2026-10-01' } }).problems[0], /expired/);
  assert.match(
    run(report(), { [id]: { ...ok, until: '2027-06-01' } }).problems[0],
    /more than 90 days/
  );
  assert.match(
    run(report(), { [id]: { ...ok, until: '2026-31-10' } }).problems[0],
    /real YYYY-MM-DD/
  );
  assert.match(run(report(), { [id]: { ...ok, reason: 42 } }).problems[0], /missing "reason"/);
  assert.match(run(report(), { [id]: { ...ok, nodes: [] } }).problems[0], /missing "nodes"/);
});

const EMPTY = { metadata: { vulnerabilities: {} }, vulnerabilities: {} };

test('an exception for an advisory that is gone is reported, never fails on expiry', () => {
  const r = run(EMPTY, { 'GHSA-gone': { ...ok, until: '2020-01-01' } });
  assert.deepEqual([r.blocking, r.problems, r.unused], [[], [], ['GHSA-gone']]);
});

test('an unused exception is still validated (dependency review waives the same ids)', () => {
  const r = run(EMPTY, { 'GHSA-other': { until: '2099-12-31' } });
  assert.equal(r.problems.length, 3); // horizon, reason, nodes
  assert.match(run(EMPTY, { 'GHSA-other': 'yes' }).problems[0], /must be an object/);
});

test('an entry with problems is not reported as covered', () => {
  const r = run(report(), { 'GHSA-aaaa-bbbb-cccc': { ...ok, until: '2026-10-01' } });
  assert.deepEqual([r.waived, r.blocking], [[], []]);
  assert.match(r.problems[0], /expired/);
});

test('an exception close to expiry warns without failing', () => {
  const r = run(report(), { 'GHSA-aaaa-bbbb-cccc': { ...ok, until: '2026-10-10' } });
  assert.deepEqual([r.problems, r.blocking], [[], []]);
  assert.match(r.warnings[0], /expires on 2026-10-10/);
});

test('an audit that did not run is never clean', () => {
  assert.throws(() => parseReport(''), /no JSON report/);
  assert.throws(() => parseReport('{"message":"ECONNREFUSED","error":{}}'), /did not complete/);
});

test('strict dates', () => {
  assert.ok(isValidDate('2026-02-28'));
  for (const bad of ['2026-02-30', '2026-31-10', '9999-99-99', '2026-1-1', 42])
    assert.equal(isValidDate(bad), false);
});

test('main: exit codes end to end through --report/--allowlist', () => {
  const dir = mkdtempSync(join(tmpdir(), 'npm-audit-'));
  const rep = join(dir, 'audit.json');
  const allow = join(dir, 'allow.json');
  writeFileSync(rep, JSON.stringify(report()));
  writeFileSync(allow, JSON.stringify({ _comment: 'x' }));
  assert.equal(main(['--report', rep, '--allowlist', allow, '--today', TODAY]), 1);
  writeFileSync(allow, JSON.stringify({ 'GHSA-aaaa-bbbb-cccc': ok }));
  assert.equal(main(['--report', rep, '--allowlist', allow, '--today', TODAY]), 0);
  writeFileSync(allow, '{ "trailing": 1, }');
  assert.throws(
    () => main(['--report', rep, '--allowlist', allow, '--today', TODAY]),
    /not valid JSON/
  );
});
