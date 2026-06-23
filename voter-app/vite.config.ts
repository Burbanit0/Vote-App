import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { VitePWA } from 'vite-plugin-pwa';
import { fileURLToPath } from 'node:url';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

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
        // The backend is FastAPI-only (Flask retired in Phase 4.5.b). Everything
        // under /api/* (the /api/v1/* public API + /api/v2/* app surface) and the
        // Socket.IO stream is served by uvicorn on :4434.
        '/api': {
          target: 'http://localhost:4434',
          changeOrigin: true,
        },
        '/socket.io': {
          target: 'http://localhost:4434',
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
              if (id.includes('jspdf') || id.includes('html2canvas')) return 'pdf';
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
      'process.env.VITE_API_URL': JSON.stringify(env.VITE_API_URL || 'http://localhost:4434'),
    },
  };
});
