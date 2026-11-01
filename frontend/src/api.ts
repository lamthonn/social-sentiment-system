/** Client gọi FastAPI backend.
 *
 * Dev: Vite proxy `/api` -> http://localhost:8000 (xem vite.config.ts),
 * nên không cần cấu hình CORS phức tạp khi phát triển local.
 * Prod: đổi VITE_API_BASE_URL (file .env) trỏ thẳng tới domain API.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

// Token đăng nhập lưu trong sessionStorage (mất khi đóng tab) - mọi request đều gửi kèm.
const TOKEN_KEY = 'sss-token'
export const auth = {
  get token(): string | null {
    try { return sessionStorage.getItem(TOKEN_KEY) } catch { return null }
  },
  set(token: string | null) {
    try {
      if (token) sessionStorage.setItem(TOKEN_KEY, token)
      else sessionStorage.removeItem(TOKEN_KEY)
    } catch { /* trình duyệt chặn storage */ }
  },
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string>) }
  if (init?.body) headers['Content-Type'] = 'application/json'
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`
  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers })
  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body)
    } catch { /* không phải JSON */ }
    if (res.status === 401 && path !== '/auth/login') {
      auth.set(null)
      window.dispatchEvent(new Event('sss-logout')) // App bắt sự kiện này để quay về màn đăng nhập
    }
    throw new ApiError(res.status, detail || `API ${path} trả về ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') q.set(k, String(v)) })
  return q.toString()
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
  category: string | null
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
  category?: string
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

export interface SchedulerStatus {
  enabled: boolean
  poll_interval_minutes: number
  next_run_at: string | null
}

export const api = {
  health: () => request<HealthResponse>('/health'),
  stats: () => request<StatsResponse>('/stats'),
  posts: ({ page = 1, pageSize = 20, platform, category }: ListPostsParams = {}) => {
    const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (platform) query.set('platform', platform)
    if (category) query.set('category', category)
    return request<PostListResponse>(`/posts?${query.toString()}`)
  },
  postCategories: () => request<string[]>('/posts/categories'),

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

  scheduler: {
    status: () => request<SchedulerStatus>('/scheduler'),
    toggle: (enabled: boolean) =>
      request<SchedulerStatus>('/scheduler/toggle', { method: 'POST', body: JSON.stringify({ enabled }) }),
  },

  // ===== webapp quản lý (api/app_routes.py) =====
  login: (username: string, password: string) =>
    request<{ token: string; user: CurrentUser }>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  me: () => request<CurrentUser>('/auth/me'),
  changePassword: (old_password: string, new_password: string) =>
    request<{ ok: boolean }>('/auth/change-password', { method: 'POST', body: JSON.stringify({ old_password, new_password }) }),
  dashboard: (days: number, category?: string) => request<DashboardSummary>(`/dashboard/summary?${qs({ days, category })}`),
  analysisPosts: (p: AnalysisQuery) => request<Paged<AnalysisPost>>(`/analysis/posts?${qs({ ...p })}`),
  topics: (category?: string) => request<TopicsResponse>(`/topics/latest?${qs({ category })}`),
  modelRuns: () => request<ModelRunInfo[]>('/models/runs'),
  experiments: () => request<ExperimentInfo[]>('/experiments'),
  selectModel: (id: number) => request<ModelRunInfo>(`/models/${id}/select`, { method: 'POST' }),
  pipelineRuns: (page: number, step?: string) => request<PipelineRunsResponse>(`/pipeline/runs?${qs({ page, step })}`),
  runStep: (body: { step: string; task?: string; model?: string; epochs?: number }) =>
    request<{ started: string }>('/pipeline/run', { method: 'POST', body: JSON.stringify(body) }),
  users: {
    list: () => request<UserInfo[]>('/users'),
    create: (body: { username: string; password: string; role: Role }) =>
      request<UserInfo>('/users', { method: 'POST', body: JSON.stringify(body) }),
    update: (id: number, body: Partial<{ role: Role; is_active: boolean; password: string }>) =>
      request<UserInfo>(`/users/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  },
  audit: (p: { page: number; username?: string; action?: string; failed_only?: boolean }) =>
    request<Paged<AuditItem>>(`/audit?${qs({ ...p, page_size: 50 })}`),
}

export type Role = 'viewer' | 'analyst' | 'admin'
export const ROLE_LABEL: Record<Role, string> = { viewer: 'Người xem', analyst: 'Phân tích viên', admin: 'Quản trị' }
export interface CurrentUser { username: string; role: Role }
export interface Paged<T> { items: T[]; total: number; page?: number; page_size?: number }

export interface DashboardSummary {
  totals: Record<string, number>
  distribution: { sentiment: Record<string, number>; emotion: Record<string, number> }
  series: { sentiment: { day: string; label: string; count: number }[]; emotion: { day: string; label: string; count: number }[] }
  by_category: { category: string; label: string; count: number }[]
  models: Record<'sentiment' | 'emotion', { run_code: string; model_name: string; f1_macro: number } | null>
  monitor: ({ at: string; alerts?: string[] } & Record<string, unknown>) | null
  categories: string[]
}

export interface AnalysisQuery {
  page: number; page_size: number; q?: string; category?: string; platform?: string; sentiment?: string; emotion?: string; include_spam?: boolean
}
export interface AnalysisPost {
  id: number; platform: string; category: string | null; author_hash: string; posted_at: string | null; collected_at: string
  text: string | null; content: string | null; lang: string | null; is_spam: boolean | null
  sentiment: string | null; sentiment_score: number | null; emotion: string | null; emotion_score: number | null
}

export interface TopicInfo {
  id: number; category: string | null; keywords: string; size: number; trend_label: string; growth: number
  sentiment_shift: string; positive_share: number; negative_share: number; neutral_share: number
  daily: { day: string; count: number; positive: number; negative: number }[]
}
export interface TopicsResponse { run: ({ id: number; finished_at: string } & Record<string, unknown>) | null; topics: TopicInfo[] }

export interface ModelRunInfo {
  id: number; run_code: string; task: 'sentiment' | 'emotion'; model_key: string; model_name: string; dataset: string
  dataset_version: string; params: Record<string, unknown>; accuracy: number; f1_macro: number; precision_macro: number
  recall_macro: number; per_class: Record<string, { precision: number; recall: number; f1: number; support: number }>
  confusion: { labels: string[]; matrix: number[][] }; train_seconds: number; selected: boolean; created_at: string
}

export interface PipelineRunInfo {
  id: number; step: string; status: string; started_at: string; finished_at: string | null; records_in: number
  records_out: number; triggered_by: string; info: Record<string, unknown> | string | null
}
export interface PipelineRunsResponse { total: number; running: string[]; items: PipelineRunInfo[] }

export interface ExperimentInfo {
  name: string; title: string; question: string; description: string; created_at: string
  tables: { title: string; columns: string[]; rows: Record<string, string | number | null>[] }[]
  findings: string[]; env: Record<string, string>
}

export interface UserInfo { id: number; username: string; role: Role; is_active: boolean; created_at: string }
export interface AuditItem { id: number; at: string; username: string | null; action: string; detail: string | null; ip: string | null; success: boolean }
