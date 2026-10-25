import process from 'node:process';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // SCRUM-13: the app calls /api on its own origin so the SameSite session cookie is sent.
    // Locally Vite forwards it to the API; on Render a rewrite in render.yaml does the same.
    // Docker Compose sets API_PROXY_TARGET, because there the API's hostname is "api".
    proxy: {
      '/api': {
        target: process.env.API_PROXY_TARGET ?? 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
