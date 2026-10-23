import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// Django runserver (backend/). The SPA and API share one origin in dev via this proxy,
// matching production, where Django serves the built SPA (docs/ARCHITECTURE.md §1).
// Casefile uses fixed ports 8010 (Django) and 5180 (Vite): 8000 and 5173 clash with other
// local projects on this machine.
const backend = process.env.CASEFILE_BACKEND_URL ?? 'http://localhost:8010'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5180,
    strictPort: true,
    proxy: {
      '/api': { target: backend, changeOrigin: false },
      '/admin': { target: backend, changeOrigin: false },
      '/static': { target: backend, changeOrigin: false },
    },
  },
})
