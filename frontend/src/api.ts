/** Client gọi FastAPI backend.
 *
 * Dev: Vite proxy `/api` -> http://localhost:8000 (xem vite.config.ts),
 * nên không cần cấu hình CORS phức tạp khi phát triển local.
 * Prod: đổi VITE_API_BASE_URL (file .env) trỏ thẳng tới domain API.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: init?.body ? { 'Content-Type': 'application/json', ...init.headers } : init?.headers,
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`API ${path} trả về ${res.status}${body ? `: ${body}` : ''}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export interface HealthResponse {
  status: string
}

export interface StatsResponse {
  total_posts: number
  analyzed: number
}

export interface RawPost {
  id: number
  platform: string
  post_id: string
  author_hash: string
  content: string
  posted_at: string | null
  collected_at: string
}

export interface PostListResponse {
  items: RawPost[]
  total: number
  page: number
  page_size: number
}

export interface ListPostsParams {
  page?: number
  pageSize?: number
  platform?: string
}

export interface SearchQuery {
  id: number
  platform: string
  query: string
  max_videos: number
  published_within_days: number
  enabled: boolean
  created_at: string
}

export type SearchQueryInput = Omit<SearchQuery, 'id' | 'created_at'>

export interface TrackedVideo {
  id: number
  platform: string
  video_id: string
  label: string | null
  enabled: boolean
  created_at: string
}

export type TrackedVideoInput = Omit<TrackedVideo, 'id' | 'created_at'>

export const api = {
  health: () => request<HealthResponse>('/health'),
  stats: () => request<StatsResponse>('/stats'),
  posts: ({ page = 1, pageSize = 20, platform }: ListPostsParams = {}) => {
    const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (platform) query.set('platform', platform)
    return request<PostListResponse>(`/posts?${query.toString()}`)
  },

  searchQueries: {
    list: () => request<SearchQuery[]>('/search-queries'),
    create: (payload: SearchQueryInput) =>
      request<SearchQuery>('/search-queries', { method: 'POST', body: JSON.stringify(payload) }),
    update: (id: number, payload: SearchQueryInput) =>
      request<SearchQuery>(`/search-queries/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
    remove: (id: number) => request<void>(`/search-queries/${id}`, { method: 'DELETE' }),
  },

  trackedVideos: {
    list: () => request<TrackedVideo[]>('/tracked-videos'),
    create: (payload: TrackedVideoInput) =>
      request<TrackedVideo>('/tracked-videos', { method: 'POST', body: JSON.stringify(payload) }),
    update: (id: number, payload: TrackedVideoInput) =>
      request<TrackedVideo>(`/tracked-videos/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
    remove: (id: number) => request<void>(`/tracked-videos/${id}`, { method: 'DELETE' }),
  },
}
