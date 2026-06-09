import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

// Resolve a path relative to this config file → absolute (for alias replacements).
const r = (p: string) => fileURLToPath(new URL(p, import.meta.url));

// Vitest config (Phase 6 — migrated from Jest/ts-jest). Mirrors the old
// jest.config.cjs: jsdom env, the same module mocks, and the same coverage
// thresholds. CSS is left at Vitest's default (CSS Modules → class-name proxy,
// like identity-obj-proxy; plain CSS imports are ignored), so no css alias.
export default defineConfig({
  plugins: [react()],
  define: {
    'process.env.VITE_API_URL': JSON.stringify(
      process.env.VITE_API_URL || 'http://localhost:4434'
    ),
  },
  resolve: {
    // Vite 8 native tsconfig `paths` resolution — resolves `@/*` (from
    // tsconfig.json) at the resolver level in EVERY context, including coverage
    // instrumentation (where the plain resolve.alias / vite-tsconfig-paths plugin
    // was unreliable on the Linux CI runner → `@/lib/utils` resolve failures).
    tsconfigPaths: true,
    // react-router v7 splits into react-router (context + hooks) and
    // react-router-dom (re-export). Tests wrap in react-router-dom's
    // MemoryRouter while components call react-router's useNavigate; dedupe so
    // they share ONE module instance (else the Router context mismatches).
    dedupe: ['react', 'react-dom', 'react-router', 'react-router-dom'],
    alias: [
      // `@/` → src as a belt-and-suspenders fallback to the native tsconfigPaths
      // above (string form, matching vite.config.ts). Must precede the regex aliases.
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
      // provider: 'v8' (NOT istanbul). Root cause of the Linux CI failure: istanbul
      // SOURCE-instruments every module, and on the GitHub runner that transform
      // dropped the `@/…` alias resolution (`vite:import-analysis` couldn't resolve
      // `@/lib/utils`), failing ~every component test under --coverage. v8 uses Node's
      // RUNTIME coverage and does NOT transform source, so `@/` resolves exactly like
      // the (passing) plain `vitest run`. Combined with NO `include` below, v8 also
      // never hits the rolldown uncovered-file parser that broke the earlier attempt.
      provider: 'v8',
      reporter: ['text', 'lcov', 'html'],
      // NO `include` + `all: false`: never scan/instrument untested files (that
      // uncovered-file pass, `?vitest-uncovered-coverage=true`, was the original
      // crash). Coverage reflects only files exercised by tests — essentially the
      // whole app, since every src file is imported by a test.
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
