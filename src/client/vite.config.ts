import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  const devCookie = env.MM_DEV_COOKIE?.trim();

  const proxyHeaders: Record<string, string> = {
    Origin: 'https://new-market-maker.dev.decodebackoffice.com',
    Referer: 'https://new-market-maker.dev.decodebackoffice.com/',
  };
  if (devCookie) proxyHeaders.Cookie = devCookie;

  return {
    base: '/dolphin-web/',
    plugins: [react()],
    server: {
      port: 5174,
      proxy: {
        '/dolphin/api': {
          target: 'https://new-market-maker.dev.decodebackoffice.com',
          changeOrigin: true,
          headers: proxyHeaders,
        },
        '/dolphin/fapi': {
          target: 'https://new-market-maker.dev.decodebackoffice.com',
          changeOrigin: true,
          headers: proxyHeaders,
        },
      },
    },
  };
});
