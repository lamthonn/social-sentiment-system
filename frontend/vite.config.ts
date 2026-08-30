import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5500,
    strictPort: true, // báo lỗi rõ ràng nếu 5500 cũng đang bị chiếm, thay vì tự nhảy sang port khác
    proxy: {
      // Dev only: forward /api/* tới FastAPI (localhost:8000) để tránh CORS
      // khi chạy `npm run dev`. Production build gọi thẳng VITE_API_BASE_URL.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
