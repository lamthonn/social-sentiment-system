import { useEffect, useState } from 'react'
import { Card, Checkbox, Input, Select, Space, Table, Tag, Typography, message } from 'antd'
import { api, type AnalysisPost, type AnalysisQuery } from './api'
import { EMOTION_COLOR, EMOTION_ORDER, LabelTag, SENTIMENT_COLOR, SENTIMENT_ORDER, fmtTime } from './ui'

const { Text, Paragraph } = Typography

export default function AnalysisPosts({ isAdmin }: { isAdmin: boolean }) {
  const [query, setQuery] = useState<AnalysisQuery>({ page: 1, page_size: 20 })
  const [data, setData] = useState<{ items: AnalysisPost[]; total: number }>({ items: [], total: 0 })
  const [categories, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => { api.postCategories().then(setCategories).catch(() => {}) }, [])
  useEffect(() => {
    setLoading(true)
    api.analysisPosts(query).then(setData).catch((e) => message.error(e.message)).finally(() => setLoading(false))
  }, [query])

  const set = (patch: Partial<AnalysisQuery>) => setQuery((q) => ({ ...q, ...patch, page: patch.page ?? 1 }))

  return (
    <Card>
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search placeholder="Tìm trong nội dung…" allowClear style={{ width: 260 }} onSearch={(v) => set({ q: v || undefined })} />
        <Select allowClear placeholder="Chủ đề thu thập" style={{ width: 200 }} options={categories.map((c) => ({ value: c, label: c }))} onChange={(v) => set({ category: v })} />
        <Select allowClear placeholder="Quan điểm" style={{ width: 140 }} options={SENTIMENT_ORDER.map((l) => ({ value: l, label: l }))} onChange={(v) => set({ sentiment: v })} />
        <Select allowClear placeholder="Cảm xúc" style={{ width: 140 }} options={EMOTION_ORDER.map((l) => ({ value: l, label: l }))} onChange={(v) => set({ emotion: v })} />
        <Select allowClear placeholder="Nền tảng" style={{ width: 120 }} options={[{ value: 'youtube', label: 'YouTube' }, { value: 'tiktok', label: 'TikTok' }]} onChange={(v) => set({ platform: v })} />
        <Checkbox onChange={(e) => set({ include_spam: e.target.checked || undefined })}>Hiện cả spam/trùng lặp</Checkbox>
      </Space>
      <Paragraph type="secondary" style={{ marginTop: -4 }}>
        Văn bản hiển thị là bản đã làm sạch: số điện thoại, email, @tên đã được che.{isAdmin ? ' Quản trị có thể mở xem nội dung gốc.' : ''}
      </Paragraph>
      <Table<AnalysisPost>
        rowKey="id" loading={loading} dataSource={data.items} size="middle"
        pagination={{ current: query.page, pageSize: query.page_size, total: data.total, showSizeChanger: true,
          showTotal: (t) => `${t} bài`, onChange: (page, page_size) => setQuery((q) => ({ ...q, page, page_size })) }}
        expandable={isAdmin ? { expandedRowRender: (r) => <Text type="secondary">Nội dung gốc: {r.content}</Text>, rowExpandable: (r) => !!r.content } : undefined}
        columns={[
          { title: 'Thời gian', dataIndex: 'posted_at', width: 150, render: (v, r) => fmtTime(v ?? r.collected_at) },
          { title: 'Chủ đề', dataIndex: 'category', width: 140, render: (v) => (v ? <Tag>{v}</Tag> : '—') },
          { title: 'Nội dung (đã làm sạch)', dataIndex: 'text', render: (v: string | null, r) => (
            <span>{v ?? <Text type="secondary">chưa làm sạch</Text>}{r.is_spam ? <Tag color="orange" style={{ marginLeft: 6 }}>spam</Tag> : null}
              {r.lang && r.lang !== 'vi' ? <Tag style={{ marginLeft: 6 }}>{r.lang}</Tag> : null}</span>
          ) },
          { title: 'Quan điểm', dataIndex: 'sentiment', width: 130, render: (v, r) => <LabelTag label={v} score={r.sentiment_score} palette={SENTIMENT_COLOR} /> },
          { title: 'Cảm xúc', dataIndex: 'emotion', width: 140, render: (v, r) => <LabelTag label={v} score={r.emotion_score} palette={EMOTION_COLOR} /> },
          { title: 'Tác giả (băm)', dataIndex: 'author_hash', width: 120, render: (v) => <Text code>{v}</Text> },
        ]}
      />
    </Card>
  )
}
