import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5182,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        configure: (proxy, options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('[PROXY] Request:', req.method, req.url)
            console.log('[PROXY] Target:', options.target)
          })
          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('[PROXY] Response:', proxyRes.statusCode)
          })
          proxy.on('error', (err, req, res) => {
            console.log('[PROXY] Error:', err)
          })
        }
      }
    }
  }
})
