import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'
import { defineConfig } from 'vite'

// HTTPS (T-27): có chứng chỉ ở data/certs/ (tạo bằng `python -m security.tls`) thì dev server chạy https.
// Chưa có -> http như cũ.
const certDir = path.resolve(import.meta.dirname, '../data/certs')
const cert = path.join(certDir, 'cert.pem')
const key = path.join(certDir, 'key.pem')
const https = fs.existsSync(cert) && fs.existsSync(key) ? { cert: fs.readFileSync(cert), key: fs.readFileSync(key) } : undefined

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5500,
    strictPort: true, // báo lỗi rõ ràng nếu 5500 cũng đang bị chiếm, thay vì tự nhảy sang port khác
    https,
    headers: https ? { 'Strict-Transport-Security': 'max-age=31536000' } : undefined,
    proxy: {
      // Dev only: forward /api/* tới FastAPI (localhost:8000) để tránh CORS
      // khi chạy `npm run dev`. Production build gọi thẳng VITE_API_BASE_URL.
      // Chặng Vite -> API nằm trong cùng máy (127.0.0.1) nên không cần TLS.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
