// What the `static` project tests (playwright.config.ts), built only when it runs: the static
// build as `npm run build:static` makes it (no tsc: the build job types it), its engine.zip,
// and the answers the engine gives under CPython, which the backend's test_browser_engine.py
// holds to the server's. PYTHON names an interpreter with the backend's packages (the e2e
// job's, which also runs the backend).
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { test as setup } from '@playwright/test';

const STATIC_DIR = 'node_modules/.e2e-static';
const PYTHON = process.env.PYTHON ?? 'python3';

setup('build the static site, its engine and the answers it must give', () => {
  setup.setTimeout(300_000);
  execFileSync('npx', ['vite', 'build', '--outDir', STATIC_DIR, '--emptyOutDir'], {
    // A production build reads .env.local / .env.production too: blank the tracker.
    env: { ...process.env, VITE_ENGINE: 'browser', VITE_UMAMI_SRC: '', VITE_UMAMI_WEBSITE_ID: '' },
  });
  for (const [script, out] of [
    ['build_browser_engine.py', 'engine.zip'],
    ['browser_engine_answers.py', 'answers.json'],
  ]) {
    execFileSync(PYTHON, [`scripts/${script}`, resolve(STATIC_DIR, out)], {
      cwd: '../fast_api_voter',
    });
  }
});
