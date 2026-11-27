import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {execSync} from 'node:child_process';

// The commit this build is from, shown in the home footer. Docker builds have no .git, so they pass GIT_SHA.
const sha = () => { try { return execSync('git rev-parse HEAD', {stdio:['ignore', 'pipe', 'ignore']}).toString().trim(); } catch { return 'dev'; } };

// `bun run dev` serves the UI with hot reload on :5173; the Go gateway (docker compose, :8000) does the rest.
// Start the gateway with DEV_ORIGIN=http://localhost:5173 so it accepts requests from this dev server.
const api = {target: 'http://localhost:8000', changeOrigin: true};
export default defineConfig({
  plugins: [react()],
  define: {__COMMIT__: JSON.stringify(process.env.GIT_SHA || sha())},
  server: {
    port: 5173,
    strictPort: true,  // DEV_ORIGIN names exactly this origin
    proxy: {'/api': {...api, ws: true}, '/courses': api, '/auth': api},
  },
});
