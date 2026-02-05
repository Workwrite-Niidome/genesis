import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// API and WebSocket URLs are configured via environment variables:
//   VITE_API_URL  — e.g., https://api.genesis-pj.net  (production)
//   VITE_WS_URL   — e.g., wss://api.genesis-pj.net    (production)
// In development, the Vite dev server proxies /api and /socket.io to localhost:8000.

export default defineConfig({
  base: '/',
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/socket.io': {
        target: process.env.VITE_WS_URL || 'http://localhost:8000',
        ws: true,
      },
    },
  },
})
