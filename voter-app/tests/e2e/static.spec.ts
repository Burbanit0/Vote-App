// The static build (PLAN_BEYOND_CI W6, option A; EXP-023): no server, the backend's own
// routers run in the page, in Pyodide (src/api/browserEngine.ts, src/workers/
// engine.worker.ts, fast_api_voter/api/browser.py). static.setup.ts builds it, with its
// engine.zip, and the `static` project serves it on :3002 (playwright.config.ts).
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { Page } from '@playwright/test';
import { loadPyodide } from 'pyodide';
import { test, expect } from './coverageFixtures';
import { STATIC_BASE } from '../../playwright.config';

const STATIC_DIR = 'node_modules/.e2e-static';

/** A request and the answer CPython's engine gave it (scripts/browser_engine_answers.py). */
interface Asked {
  method: string;
  path: string;
  query: string;
  body: unknown;
  status: number;
  answer: Record<string, unknown>;
  exact: boolean;
}

/** JSON with numbers to 12 significant digits: numpy in wasm and on x86 may part in the last bits. */
const canonical = (value: unknown) =>
  JSON.stringify(value, (_key, v) => (typeof v === 'number' ? Number(v.toPrecision(12)) : v));

/** Where two answers part, with some context: the CI log alone shows what differs. */
function difference(cpython: string, pyodide: string): string {
  let i = 0;
  while (i < cpython.length && cpython[i] === pyodide[i]) i++;
  const from = Math.max(0, i - 40);
  return `CPython …${cpython.slice(from, i + 40)}… Pyodide …${pyodide.slice(from, i + 40)}…`;
}

// Every route the engine serves, as CPython answers it (which the backend's
// test_browser_engine.py holds to the server's answer): the same status and JSON, or, for
// an unseeded route, the same status and keys. The engine here is the static build's own
// engine.zip, under Pyodide in Node, as the page's worker loads it.
test('the engine in the page answers every route as the server does', async () => {
  test.setTimeout(300_000);
  // The Pyodide tested here is the one the page loads from the CDN.
  const { version } = JSON.parse(readFileSync('node_modules/pyodide/package.json', 'utf8'));
  expect(readFileSync('src/workers/engine.worker.ts', 'utf8')).toContain(`/pyodide/v${version}/`);
  // Pyodide finds its own files from its call stack, which Playwright's source maps
  // misplace: name the folder (the runner's working directory is voter-app/).
  const py = await loadPyodide({ indexURL: `${resolve('node_modules/pyodide')}/` });
  py.unpackArchive(new Uint8Array(readFileSync(`${STATIC_DIR}/engine.zip`)), 'zip', {
    extractDir: '/engine',
  });
  const { packages } = JSON.parse(py.FS.readFile('/engine/engine.json', { encoding: 'utf8' }));
  await py.loadPackage(packages, { messageCallback: () => {} });
  py.runPython("import sys; sys.path.insert(0, '/engine')");
  const handle = py.pyimport('api.browser').handle;

  const asked: Asked[] = JSON.parse(readFileSync(`${STATIC_DIR}/answers.json`, 'utf8'));
  const differ: string[] = [];
  for (const { method, path, query, body, status, answer, exact } of asked) {
    const result = await handle(method, path, query, body == null ? '' : JSON.stringify(body));
    const [engineStatus, text] = result.toJs();
    result.destroy();
    const engineAnswer = JSON.parse(text);
    const [expected, got] = exact
      ? [canonical(answer), canonical(engineAnswer)]
      : [canonical(Object.keys(answer)), canonical(Object.keys(engineAnswer))];
    if (engineStatus !== status || expected !== got) {
      differ.push(`${method} ${path}: ${status} vs ${engineStatus}, ${difference(expected, got)}`);
    }
  }
  expect(asked.length).toBeGreaterThan(50);
  expect(differ).toEqual([]);
});

/** Block every /api request at the browser and record it: none may escape the worker. */
async function withoutServer(page: Page): Promise<string[]> {
  const escaped: string[] = [];
  await page.route('**/*', (route) => {
    const { pathname } = new URL(route.request().url());
    if (!pathname.startsWith('/api')) return route.continue();
    escaped.push(`${route.request().method()} ${pathname}`);
    return route.abort();
  });
  return escaped;
}

// Pages under the base path (playwright.config.ts's STATIC_BASE), so each goto is relative.
// vite preview answers any path with the page; GitHub Pages answers a deep link with
// 404.html, which must be the page itself.
test('the static build answers a deep link with the page itself', () => {
  expect(readFileSync(`${STATIC_DIR}/404.html`)).toEqual(readFileSync(`${STATIC_DIR}/index.html`));
});

test('the playground, the fiches and Polity work with no server', async ({ page }) => {
  test.setTimeout(240_000);
  const escaped = await withoutServer(page);
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));

  await page.goto('playground');
  await expect(page.getByTestId('cycle-rate')).toContainText(/\d/, { timeout: 90_000 });

  // The navbar's links load a whole page: they must carry the base path.
  await page.getByTestId('nav-laboratoire').click();
  await expect(page).toHaveURL(new RegExp(`${STATIC_BASE}laboratoire$`));
  await expect(page.getByTestId('nav-laboratoire')).toHaveAttribute('aria-current', 'page');

  await page.goto('laboratoire?exp=sys-stv');
  await page.getByTestId('stv-run').click();
  await expect(page.getByTestId('stv-round-0')).toBeVisible({ timeout: 60_000 });

  await page.goto('laboratoire?exp=thy-polis');
  await page.getByTestId('simulate-btn').click();
  await expect(page.getByTestId('polis-scatter-svg')).toBeVisible({ timeout: 60_000 });

  // Over HTTP: the static build has no Socket.IO, so no streaming switch either.
  await page.goto('laboratoire?exp=ana-montecarlo');
  await page.getByTestId('mc-run').click();
  await expect(page.getByTestId('mc-results')).toBeVisible({ timeout: 120_000 });
  await expect(page.locator('#streaming-toggle')).toHaveCount(0);

  // Polity's explorer, from its export (src/api/staticPolity.ts): the three full runs.
  await page.goto('polity?citizen=3');
  await expect(page.getByTestId('polity-run-picker').locator('option')).toHaveCount(3);
  await expect(page.getByTestId('polity-fact-population')).toContainText('500');
  await expect(page.getByTestId('polity-map-canvas')).toBeVisible();
  await expect(page.getByTestId('polity-biography')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('polity-biography-error')).toHaveCount(0);

  expect(escaped).toEqual([]);
  expect(errors).toEqual([]);
});
