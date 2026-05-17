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
        '/api/election': {
          target: 'http://localhost:4433',
          changeOrigin: true,
        },
      },
    },
    preview: {
      port: 3000,
    },
    build: {
      outDir: 'build',
      sourcemap: false,
    },
    envPrefix: 'VITE_',
    define: {
      'process.env.VITE_API_URL': JSON.stringify(
        env.VITE_API_URL || 'http://localhost:4433'
      ),
    },
  };
});
