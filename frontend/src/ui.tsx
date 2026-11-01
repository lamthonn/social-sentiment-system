// Màu và nhãn dùng chung cho mọi màn hình (một nhãn = một màu ở mọi nơi).
import { Empty, Tag } from 'antd'
import type { ReactNode } from 'react'

export const SENTIMENT_COLOR: Record<string, string> = { 'Tích cực': '#16a34a', 'Trung tính': '#9ca3af', 'Tiêu cực': '#dc2626' }
export const EMOTION_COLOR: Record<string, string> = {
  'Vui vẻ': '#16a34a', 'Buồn bã': '#2563eb', 'Tức giận': '#dc2626', 'Ghê tởm': '#7c3aed',
  'Sợ hãi': '#d97706', 'Ngạc nhiên': '#0891b2', 'Khác': '#9ca3af',
}
export const SENTIMENT_ORDER = ['Tích cực', 'Trung tính', 'Tiêu cực']
export const EMOTION_ORDER = ['Vui vẻ', 'Ngạc nhiên', 'Khác', 'Buồn bã', 'Sợ hãi', 'Tức giận', 'Ghê tởm']
export const TREND_TAG: Record<string, string> = { 'Mới nổi': 'purple', 'Đang tăng': 'volcano', 'Đang giảm': 'blue', 'Ổn định': 'default', 'Chưa đủ dữ liệu': 'default' }
export const SHIFT_TAG: Record<string, string> = { 'Tích cực hóa': 'green', 'Tiêu cực hóa': 'red', 'Ổn định': 'default', 'Chưa đủ dữ liệu': 'default' }
export const RUN_STATUS: Record<string, { color: string; label: string }> = {
  success: { color: 'success', label: 'Thành công' }, failed: { color: 'error', label: 'Lỗi' },
  running: { color: 'processing', label: 'Đang chạy' }, skipped: { color: 'default', label: 'Bỏ qua' },
}
export const STEP_LABEL: Record<string, string> = {
  collect: 'Thu thập', clean: 'Làm sạch', datasets: 'Chuẩn bị dataset', 'train:sentiment': 'Huấn luyện – quan điểm',
  'train:emotion': 'Huấn luyện – cảm xúc', predict: 'Dự đoán', trends: 'Xu hướng', monitor: 'Giám sát',
}
export const TASK_LABEL: Record<string, string> = { sentiment: 'Quan điểm 3 lớp (UIT-VSFC)', emotion: 'Cảm xúc 7 nhãn (UIT-VSMEC)' }

export function LabelTag({ label, score, palette }: { label: string | null; score?: number | null; palette: Record<string, string> }) {
  if (!label) return <span style={{ color: '#9ca3af' }}>—</span>
  return (
    <Tag color={palette[label] ?? 'default'} style={{ marginInlineEnd: 0 }}>
      {label}{score != null ? ` ${Math.round(score * 100)}%` : ''}
    </Tag>
  )
}

export const fmtTime = (v: string | null | undefined) => (v ? new Date(v.endsWith('Z') || v.includes('+') ? v : `${v}Z`).toLocaleString('vi-VN') : '—')
export const pct = (v: number) => `${(v * 100).toFixed(1)}%`

export function EmptyHint({ children }: { children: ReactNode }) {
  return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: '#6b7280' }}>{children}</span>} />
}
