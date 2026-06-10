import { defineConfig } from 'vitest/config';
import type { Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { existsSync, statSync } from 'node:fs';

// Resolve a path relative to this config file → absolute (for alias replacements).
const r = (p: string) => fileURLToPath(new URL(p, import.meta.url));

// `@/…` → src resolver implemented as an `enforce: 'pre'` plugin that returns a
// fully-resolved ABSOLUTE FILE PATH via raw fs — deliberately NOT delegating to
// Vite's resolver (resolve.alias / tsconfigPaths / this.resolve).
//
// History: under `vitest run --coverage` on the GitHub Linux runner, EVERY `@/…`
// import failed with `Failed to resolve import "@/lib/utils"` (vite:import-analysis),
// while `vite build` and plain `vitest run` resolved it fine. We tried resolve.alias,
// native resolve.tsconfigPaths, vite-tsconfig-paths, and an enforce:pre plugin that
// delegated to `this.resolve` — ALL passed locally and ALL failed on that runner.
// That rules out "which alias mechanism" and points at Vite's underlying (native
// rolldown/oxc) resolver mis-resolving the aliased path specifically in the coverage
// fetch context. So we stop routing through it: probe the filesystem ourselves and
// return a concrete `<src>/x.tsx` path that needs no further resolution. Non-JS/TS
// or unfound specifiers fall through (return null) so Vite handles them as before.
const AT_EXTS = ['', '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.json'];
const resolveAtPath = (srcDir: string, source: string): string | null => {
  const base = source === '@' ? srcDir : `${srcDir}/${source.slice(2)}`;
  for (const ext of AT_EXTS) {
    const p = base + ext;
    if (existsSync(p) && statSync(p).isFile()) return p;
  }
  for (const ext of AT_EXTS) {
    if (!ext) continue;
    const p = `${base}/index${ext}`;
    if (existsSync(p)) return p;
  }
  return null;
};
let _atDiagLogged = false; // TEMP diagnostic — remove once CI is confirmed green.
const atAlias = (srcDir: string): Plugin => ({
  name: 'vote-app:at-alias',
  enforce: 'pre',
  resolveId(source) {
    if (source === '@' || source.startsWith('@/')) {
      const resolved = resolveAtPath(srcDir, source);
      if (!_atDiagLogged) {
        _atDiagLogged = true;
        // eslint-disable-next-line no-console
        console.error(`[atAlias] plugin active — ${source} -> ${resolved}`);
      }
      return resolved;
    }
    return null;
  },
});

// Vitest config (Phase 6 — migrated from Jest/ts-jest). Mirrors the old
// jest.config.cjs: jsdom env, the same module mocks, and the same coverage
// thresholds. CSS is left at Vitest's default (CSS Modules → class-name proxy,
// like identity-obj-proxy; plain CSS imports are ignored), so no css alias.
export default defineConfig({
  plugins: [atAlias(r('./src')), react()],
  define: {
    'process.env.VITE_API_URL': JSON.stringify(
      process.env.VITE_API_URL || 'http://localhost:4434'
    ),
  },
  resolve: {
    // NB: `@/…` is resolved by the `atAlias` plugin above (NOT here) — see its
    // comment for why the plugin is required for coverage on the Linux CI runner.
    // react-router v7 splits into react-router (context + hooks) and
    // react-router-dom (re-export). Tests wrap in react-router-dom's
    // MemoryRouter while components call react-router's useNavigate; dedupe so
    // they share ONE module instance (else the Router context mismatches).
    dedupe: ['react', 'react-dom', 'react-router', 'react-router-dom'],
    alias: [
      // The app mixes `react-router` (65 files) and `react-router-dom` (re-export,
      // 9 files) imports. Under Vitest those resolve to two module instances →
      // two Router contexts → "useNavigate must be inside a Router". react-router-dom@7
      // just re-exports react-router and the app only uses shared exports, so collapse
      // them to ONE instance for tests.
      { find: /^react-router-dom$/, replacement: 'react-router' },
      // virtual:pwa-register/react → no-op mock (was moduleNameMapper in Jest)
      { find: /^virtual:pwa-register\/react$/, replacement: r('./src/__mocks__/pwa-register.ts') },
      // useSimulationWorker uses `new Worker(new URL(..., import.meta.url))` →
      // replace project-wide with the no-op mock so chart/heatmap tests work.
      // NB: Vite regex aliases do a *substring* replace, so anchor with ^.* to
      // swallow the whole specifier (else the `../../` prefix is kept → bad path).
      { find: /^.*hooks\/useSimulationWorker$/, replacement: r('./src/__mocks__/useSimulationWorker.ts') },
      // Static image imports → file stub.
      { find: /^.*\.(jpg|jpeg|png|gif|webp|svg)$/, replacement: r('./src/__mocks__/fileMock.ts') },
    ],
  },
  test: {
    globals: true,
    environment: 'jsdom',
    // Match Jest's default testURL (http://localhost/) so history.replaceState
    // to same-origin paths like /app doesn't throw a jsdom SecurityError.
    environmentOptions: { jsdom: { url: 'http://localhost/' } },
    // Process CSS Modules (so `import styles from './x.module.css'` has a default
    // export of class names); plain CSS imports stay ignored (no-op).
    css: { include: [/\.module\.css$/], modules: { classNameStrategy: 'non-scoped' } },
    setupFiles: ['./src/setupTests.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    coverage: {
      // provider: 'v8' (runtime coverage, no source transform). The Linux-CI
      // `@/lib/utils` resolve failure under --coverage is fixed by the `atAlias`
      // plugin above, not here — see that comment.
      provider: 'v8',
      reporter: ['text', 'lcov', 'html'],
      // NO `include`: never scan/instrument untested files (that uncovered-file
      // pass, `?vitest-uncovered-coverage=true`, was a rolldown-parser crash on
      // Linux). Coverage reflects only files exercised by tests — essentially the
      // whole app, since every src file is imported by a test.
      exclude: [
        'src/**/*.d.ts',
        'src/index.tsx',
        'src/reportWebVitals.ts',
        'src/declarations.d.ts',
        'src/**/*.test.{ts,tsx}',
        'src/**/*.stories.{ts,tsx}',
      ],
      thresholds: {
        branches: 20,
        functions: 25,
        lines: 50,
        statements: 50,
      },
    },
  },
});
