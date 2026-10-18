import { defineConfig } from 'vite';
export default defineConfig({ root: 'apps/desktop', clearScreen: false, server: { port: 1420, strictPort: true, host: '127.0.0.1' }, build: { outDir: 'dist', emptyOutDir: true } });
