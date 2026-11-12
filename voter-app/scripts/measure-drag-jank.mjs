#!/usr/bin/env node
/**
 * measure-drag-jank.mjs — PLAN_BEYOND_CI W3.6's "measure only": how much the main thread
 * blocks while a candidate is dragged by touch on a phone, with the CPU throttled 4×.
 *
 * Six one-second drags of candidate 0 on /playground (the Galaxy S24 profile the e2e
 * mobile project uses), about 30 touch moves a second, alternating direction so each
 * one moves it. It counts the long tasks (over 50 ms, the Long Tasks API) during each
 * drag, and lists those that follow the lift.
 *
 * Usage: serve a production build on :3000 with the backend on :4434, as the e2e suite
 * does (playwright.config.ts's webServer), then:
 *   npm run measure:jank [-- base-url]
 */
import { chromium, devices } from '@playwright/test';

const base = process.argv[2] ?? 'http://localhost:3000';
const browser = await chromium.launch();
const page = await browser.newPage({ ...devices['Galaxy S24'], locale: 'fr-FR' });
await page.goto(`${base}/playground`);
const dot = page.getByTestId('candidate-0').locator('circle').last();
await dot.scrollIntoViewIfNeeded();
// Panels above the map fill in late: let the layout settle before the first touch.
await page.waitForTimeout(1500);

const cdp = await page.context().newCDPSession(page);
await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
await page.evaluate(() => {
  globalThis.longTasks = [];
  new PerformanceObserver((list) => {
    for (const e of list.getEntries()) globalThis.longTasks.push([e.startTime, e.duration]);
  }).observe({ type: 'longtask' });
});
const touch = (type, x, y) =>
  cdp.send('Input.dispatchTouchEvent', {
    type,
    touchPoints: type === 'touchEnd' ? [] : [{ x, y }],
  });

for (let run = 1; run <= 6; run++) {
  const dir = run % 2 ? -1 : 1;
  const box = await dot.boundingBox();
  let [x, y] = [box.x + box.width / 2, box.y + box.height / 2];
  const cx = await dot.getAttribute('cx');
  const start = await page.evaluate(() => {
    globalThis.longTasks = [];
    return performance.now();
  });
  const t0 = Date.now();
  await touch('touchStart', x, y);
  let moves = 0;
  while (Date.now() - t0 < 1000) {
    x += 1.5 * dir;
    y += 0.3 * dir;
    await touch('touchMove', x, y);
    moves++;
    await new Promise((r) => setTimeout(r, Math.max(0, t0 + moves * 33 - Date.now())));
  }
  await touch('touchEnd');
  const ms = Date.now() - t0;
  await page.waitForTimeout(1500);
  const tasks = await page.evaluate(() => globalThis.longTasks);
  const during = tasks.filter(([s]) => s - start < ms).map(([, d]) => d);
  const blocking = during.reduce((sum, d) => sum + d - 50, 0) / (ms / 1000);
  const after = tasks
    .filter(([s]) => s - start >= ms)
    .map(([s, d]) => `${Math.round(d)} ms at +${Math.round(s - start - ms)} ms`);
  console.log(
    `drag ${run}: ${moves} moves in ${ms} ms, cx ${cx} -> ${await dot.getAttribute('cx')}; ` +
      `during: ${during.length} long tasks, ${Math.round(blocking)} ms blocking/s; ` +
      `after the lift: ${after.join(', ') || 'none'}`
  );
}
await browser.close();
