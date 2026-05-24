import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        devOptions: {
          enabled: false,
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
          runtimeCaching: [
            {
              urlPattern: /^http:\/\/localhost:4433\/api\/(v1\/methods|scenarios\/gallery\/featured)/,
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
          theme_color: '#0d6efd',
          background_color: '#ffffff',
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
    ],
    server: {
      port: 3000,
      open: true,
      proxy: {
        // Route /api/v2/* to FastAPI (port 4434) — added in Phase 2 of the
        // strategic refactor (see STRATEGIC_REFACTOR_PLAN.md). Ordering
        // matters: the more specific prefix must come first.
        '/api/v2': {
          target: 'http://localhost:4434',
          changeOrigin: true,
        },
        // Everything else still hits Flask (port 4433). As routes migrate
        // from Flask to FastAPI in Phase 3, they'll move from /api/* to
        // /api/v2/*, with /api/v1/* kept as a temporary alias.
        '/api': {
          target: 'http://localhost:4433',
          changeOrigin: true,
        },
        '/socket.io': {
          target: 'http://localhost:4433',
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
              if (id.includes('recharts'))                          return 'recharts';
              if (/[\\/]d3-(delaunay|hexbin|force)[\\/]/.test(id))  return 'd3';
              if (id.includes('jspdf') || id.includes('html2canvas')) return 'pdf';
              if (id.includes('react-bootstrap') || /[\\/]bootstrap[\\/]/.test(id)) return 'bootstrap';
            }
            return undefined;
          },
        },
      },
    },
    envPrefix: 'VITE_',
    define: {
      'process.env.VITE_API_URL': JSON.stringify(
        env.VITE_API_URL || 'http://localhost:4433'
      ),
    },
  };
});
