import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// The built SPA is served by FastAPI from `frontend/dist` (ADR-0009), so there
// is no Node runtime at the substation. During development Vite serves the app
// and proxies /api to the backend, which keeps the frontend same-origin in both
// modes and avoids a CORS-only code path that production never exercises.
const BACKEND = process.env.BI_API_URL ?? 'http://127.0.0.1:8080'

export default defineConfig({
  // Tailwind v4 is configured in CSS (`src/styles.css`), not in a JS config
  // file — there is no tailwind.config.ts to keep in sync (ADR-0014).
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
  },
})
