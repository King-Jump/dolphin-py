import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://3.1.221.68:8763', changeOrigin: true },
      '/fapi': { target: 'http://3.1.221.68:8763', changeOrigin: true },
    },
  },
});
