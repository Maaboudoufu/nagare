import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

// `bun run dev` serves the UI with hot reload on :5173; the Go gateway (docker compose, :8000) does the rest.
// Start the gateway with DEV_ORIGIN=http://localhost:5173 so it accepts requests from this dev server.
const api = {target: 'http://localhost:8000', changeOrigin: true};
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,  // DEV_ORIGIN names exactly this origin
    proxy: {'/api': {...api, ws: true}, '/courses': api, '/auth': api},
  },
});
