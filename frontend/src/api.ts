/** Client gọi FastAPI backend.
 *
 * Dev: Vite proxy `/api` -> http://localhost:8000 (xem vite.config.ts),
 * nên không cần cấu hình CORS phức tạp khi phát triển local.
 * Prod: đổi VITE_API_BASE_URL (file .env) trỏ thẳng tới domain API.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

async function request<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) {
    throw new Error(`API ${path} trả về ${res.status}`)
  }
  return res.json() as Promise<T>
}

export interface HealthResponse {
  status: string
}

export interface StatsResponse {
  total_posts: number
  analyzed: number
}

export const api = {
  health: () => request<HealthResponse>('/health'),
  stats: () => request<StatsResponse>('/stats'),
}
