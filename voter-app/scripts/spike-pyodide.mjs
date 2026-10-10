#!/usr/bin/env node
/**
 * spike-pyodide.mjs — W6 spike: three Lab fiches, on the backend and in Pyodide.
 *
 * For each engine and device (desktop; the Galaxy S24 profile, main thread throttled 4×),
 * a fresh browser context (an empty HTTP cache) opens each fiche, runs it twice, and
 * reads the two calls' times from the fetch hook (src/api/pyEngine.ts). It also sums
 * the bytes the context downloaded.
 *
 * Usage: build public/pyengine.zip (`python -m pyodide_spike.build_bundle
 * ../voter-app/public/pyengine.zip` in fast_api_voter/), serve a production build on
 * :3000 with the backend on :4434, then: node scripts/spike-pyodide.mjs [base-url]
 */
import { chromium, devices } from '@playwright/test';

const base = process.argv[2] ?? 'http://localhost:3000';
// [fiche, route, its run button, a step before running]. STV's panel starts at 3 seats
// while its slider stops at 2 on three candidates, and the backend refuses 3: set 2.
const FICHES = [
  ['thy-polis', '/api/v2/tech/polis', (p) => p.getByTestId('simulate-btn')],
  [
    'sys-stv',
    '/api/v2/election/stv',
    (p) => p.getByRole('button', { name: /^🔄/ }),
    (p) => p.locator('input[type="range"][max="2"]').first().fill('2'),
  ],
  [
    'dyn-polarization',
    '/api/v2/election/polarization',
    (p) => p.getByRole('button', { name: '📊 Calculer', exact: true }),
  ],
];
const DEVICES = [
  ['desktop', {}, 1],
  ['phone', devices['Galaxy S24'], 4],
];
const browser = await chromium.launch();
for (const [device, profile, rate] of DEVICES) {
  for (const engine of ['backend', 'pyodide']) {
    const ctx = await browser.newContext({ ...profile, locale: 'fr-FR', serviceWorkers: 'block' });
    let bytes = 0;
    ctx.on('requestfinished', async (r) => {
      const s = await r.sizes().catch(() => null);
      if (s) bytes += s.responseBodySize + s.responseHeadersSize;
    });
    const page = await ctx.newPage();
    page.on(
      'console',
      (m) => m.text().startsWith('[pyodide] ready') && console.log('   ', m.text())
    );
    const cdp = await ctx.newCDPSession(page);
    await cdp.send('Emulation.setCPUThrottlingRate', { rate });
    const t0 = Date.now();
    for (const [exp, path, button, prepare] of FICHES) {
      await page.goto(`${base}/laboratoire?exp=${exp}&engine=${engine}`);
      await prepare?.(page);
      const times = [];
      for (let i = 0; i < 2; i++) {
        const n = await page.evaluate(
          (p) => (globalThis.engineCalls ?? []).filter((c) => c.path === p).length,
          path
        );
        await button(page).click();
        await page.waitForFunction(
          ([p, n]) => (globalThis.engineCalls ?? []).filter((c) => c.path === p).length > n,
          [path, n],
          { timeout: 120_000 }
        );
        const calls = await page.evaluate(
          (p) => globalThis.engineCalls.filter((c) => c.path === p),
          path
        );
        const last = calls[calls.length - 1];
        times.push(`${last.ms} ms${last.status === 200 ? '' : ` (${last.status})`}`);
      }
      console.log(`${device} ${engine} ${exp}: first ${times[0]}, second ${times[1]}`);
    }
    console.log(
      `${device} ${engine}: ${(bytes / 1e6).toFixed(1)} MB downloaded, ${((Date.now() - t0) / 1000).toFixed(1)} s in all`
    );
    await ctx.close();
  }
}
await browser.close();
