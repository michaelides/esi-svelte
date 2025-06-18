import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      // Proxy API requests to the FastAPI backend
      // This assumes FastAPI is running on http://localhost:8000
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true, // Recommended for virtual hosted sites
        // secure: false, // Uncomment if your backend is HTTPS and has self-signed cert in dev
        // rewrite: (path) => path.replace(/^\/api/, ''), // Use if backend doesn't expect /api prefix
      }
    }
  }
});
