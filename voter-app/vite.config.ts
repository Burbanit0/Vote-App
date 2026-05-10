import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // Load .env files so we can read VITE_* vars in define below
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],
    server: {
      port: 3000,
      open: true,
    },
    preview: {
      port: 3000,
    },
    build: {
      outDir: 'build',
      sourcemap: false,
    },
    envPrefix: 'VITE_',
    // Expose VITE_ vars via process.env so code is compatible with Jest too
    define: {
      'process.env.VITE_API_URL': JSON.stringify(
        env.VITE_API_URL || 'http://localhost:4433'
      ),
    },
  };
});
