import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import { fileURLToPath } from 'node:url';

// Resolve a path relative to this config file → absolute (for alias replacements).
const r = (p: string) => fileURLToPath(new URL(p, import.meta.url));

// Vitest config (Phase 6 — migrated from Jest/ts-jest). Mirrors the old
// jest.config.cjs: jsdom env, the same module mocks, and the same coverage
// thresholds. CSS is left at Vitest's default (CSS Modules → class-name proxy,
// like identity-obj-proxy; plain CSS imports are ignored), so no css alias.
export default defineConfig({
  // tsconfigPaths resolves `@/*` (from tsconfig paths) at the RESOLVER level, so it
  // works in every transform context — including coverage instrumentation, where a
  // plain resolve.alias regex was silently dropped on the Linux CI runner (causing
  // `@/lib/utils` resolve failures + "0 test" cascades under --coverage).
  plugins: [tsconfigPaths(), react()],
  define: {
    'process.env.VITE_API_URL': JSON.stringify(
      process.env.VITE_API_URL || 'http://localhost:4434'
    ),
  },
  resolve: {
    // react-router v7 splits into react-router (context + hooks) and
    // react-router-dom (re-export). Tests wrap in react-router-dom's
    // MemoryRouter while components call react-router's useNavigate; dedupe so
    // they share ONE module instance (else the Router context mismatches).
    dedupe: ['react', 'react-dom', 'react-router', 'react-router-dom'],
    alias: [
      // shadcn `@/` → src. Use the SAME string-alias form as vite.config.ts
      // (`{ find: '@', replacement: <abs src> }`) rather than a regex: the regex
      // form isn't honoured by the coverage-instrumentation transform on the
      // Linux CI runner, so `@/lib/utils` fails to resolve under --coverage
      // (cascading to "0 test" + a failed uncovered-coverage pass). Must precede
      // the regex aliases below.
      { find: '@', replacement: r('./src') },
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
      // istanbul (not v8): instruments through Vitest's normal Vite transform.
      // The v8 provider parses uncovered files with rolldown's native parser,
      // which chokes on TS/TSX on the Linux CI runner (rolldown 1.0.0-rc.*),
      // failing the coverage step. istanbul sidesteps that path.
      provider: 'istanbul',
      reporter: ['text', 'lcov', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      // Do NOT load/instrument untested files to report them at 0%. That pass
      // (`?vitest-uncovered-coverage=true`) bypasses the resolver on the Linux CI
      // runner and fails to resolve `@/…` imports, crashing the coverage step.
      // With `all: false` coverage reflects files actually exercised by tests.
      all: false,
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
