import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

// `bun run dev` serves the UI with hot reload on :5173; the Go gateway (docker compose, :8000) does the rest.
const api = {target: 'http://localhost:8000', changeOrigin: true};
export default defineConfig({
  plugins: [react()],
  build: {chunkSizeWarningLimit: 700},  // main chunk is React + CodeMirror + Vim keys; xterm is split out
  server: {
    port: 5173,
    strictPort: true,  // the gateway trusts exactly this dev origin
    proxy: {'/api': {...api, ws: true}, '/courses': api, '/auth': api},
  },
});
