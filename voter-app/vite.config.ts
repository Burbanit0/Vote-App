import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { VitePWA } from 'vite-plugin-pwa';
import istanbul from 'vite-plugin-istanbul';
import { fileURLToPath } from 'node:url';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // Runtime coverage under the real e2e suite (Lot 6, PLAN_SOLIDITE_TECHNIQUE.md):
  // opt-in only, via E2E_COVERAGE=true, never on by default — Istanbul's Babel
  // instrumentation adds real transform overhead we don't want on every `npm
  // start`/`npm run build`. `scripts/e2e_coverage.sh` sets this env var itself.
  const coverageEnabled = process.env.E2E_COVERAGE === 'true';

  return {
    resolve: {
      alias: {
        // shadcn/ui convention: `@/` → src (Tailwind migration, Phase 6).
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    plugins: [
      react(),
      tailwindcss(),
      VitePWA({
        registerType: 'autoUpdate',
        devOptions: {
          enabled: false,
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
          runtimeCaching: [
            {
              urlPattern:
                /^http:\/\/localhost:4434\/api\/(v1\/methods|scenarios\/gallery\/featured)/,
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'api-cache',
                expiration: { maxAgeSeconds: 3600 },
              },
            },
          ],
        },
        manifest: {
          name: 'Vote Lab — Théorie du vote',
          short_name: 'Vote Lab',
          description: 'Explorez et comparez 15 méthodes de vote',
          theme_color: '#0e7068',
          background_color: '#f6f7f4',
          display: 'standalone',
          start_url: '/',
          scope: '/',
          icons: [
            {
              src: '/icons/pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png',
            },
            {
              src: '/icons/pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any maskable',
            },
          ],
        },
      }),
      // Instruments src/** with Istanbul counters (window.__coverage__) so a
      // real Playwright e2e pass can report what it actually executed —
      // conditional because it's diagnostic tooling (Lot 6), not something
      // that should touch the code path everyone builds/dev-serves normally.
      coverageEnabled &&
        istanbul({
          include: 'src/*',
          exclude: ['node_modules', 'src/**/*.test.*', 'src/lib/__fixtures__/**'],
          extension: ['.js', '.jsx', '.ts', '.tsx'],
          requireEnv: false,
          forceBuildInstrument: true,
        }),
    ],
    server: {
      port: 3000,
      open: true,
      proxy: {
        // The backend is FastAPI-only (Flask retired in Phase 4.5.b). Everything
        // under /api/* (the /api/v1/* public API + /api/v2/* app surface) and the
        // Socket.IO stream is served by uvicorn on :4434 by default.
        // Anchored on the segment, not the prefix: a plain '/api' key also
        // swallows sibling paths like the legacy '/api-docs' route, which must
        // reach the SPA (nginx serves it from index.html in production).
        // Same VITE_API_URL override as src/api/client.ts's API_BASE below —
        // needed by scripts/e2e_coverage.sh (Lot 6) to point at a coverage-
        // instrumented backend on a non-default port when :4434 is already
        // taken by something else in the dev environment.
        '^/api/': {
          target: env.VITE_API_URL || 'http://localhost:4434',
          changeOrigin: true,
        },
        '/socket.io': {
          target: env.VITE_API_URL || 'http://localhost:4434',
          changeOrigin: true,
          ws: true,
        },
      },
    },
    preview: {
      port: 3000,
    },
    build: {
      outDir: 'build',
      sourcemap: false,
      // Manual vendor splits so heavy libs (recharts, d3, jspdf) land in
      // separate chunks that the browser can cache long-term and that pages
      // not needing them never have to download.
      rollupOptions: {
        output: {
          manualChunks(id: string): string | undefined {
            if (id.includes('node_modules')) {
              if (id.includes('recharts')) return 'recharts';
              if (/[\\/]d3-(delaunay|hexbin|force)[\\/]/.test(id)) return 'd3';
              if (id.includes('react-bootstrap') || /[\\/]bootstrap[\\/]/.test(id))
                return 'bootstrap';
            }
            return undefined;
          },
        },
      },
    },
    envPrefix: 'VITE_',
    define: {
      // Single-origin prod: default to '' (same-origin, relative /api + /socket.io)
      // so the FastAPI container that serves this build also answers the API.
      // Dev keeps the explicit localhost:4434 backend. An explicit env var wins.
      'process.env.VITE_API_URL': JSON.stringify(
        env.VITE_API_URL ?? (mode === 'production' ? '' : 'http://localhost:4434')
      ),
      'process.env.VITE_SOCKET_URL': JSON.stringify(
        env.VITE_SOCKET_URL ?? (mode === 'production' ? '' : 'http://localhost:4434')
      ),
    },
  };
});
