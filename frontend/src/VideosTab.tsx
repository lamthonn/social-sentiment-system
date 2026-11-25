import { useEffect, useState } from 'react'
import { Descriptions, Drawer, Input, List, Select, Space, Spin, Table, Tag, Typography, message } from 'antd'
import type { TablePaginationConfig } from 'antd/es/table'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from 'recharts'
import { api, type VideoDetail, type VideoInfo } from './api'

const { Text, Link } = Typography

const num = (v: number | null) => (v === null ? '—' : v.toLocaleString('vi-VN'))
// API trả giờ UTC không có hậu tố múi giờ -> thêm 'Z' để trình duyệt đổi sang giờ máy
const when = (v: string | null) => (v ? new Date(v + 'Z').toLocaleString('vi-VN') : '—')
const youtubeUrl = (id: string) => `https://www.youtube.com/watch?v=${id}`

function VideoDrawer({ videoId, onClose }: { videoId: string | null; onClose: () => void }) {
  const [detail, setDetail] = useState<VideoDetail | null>(null)

  useEffect(() => {
    setDetail(null)
    if (!videoId) return
    api.videos.detail(videoId).then(setDetail).catch(() => message.error('Không tải được chi tiết video'))
  }, [videoId])

  const v = detail?.video
  const series = (detail?.snapshots ?? []).map((s) => ({
    time: new Date(s.captured_at + 'Z').toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }),
    views: s.view_count,
    likes: s.like_count,
  }))

  return (
    <Drawer open={!!videoId} onClose={onClose} width={720} title={v?.title ?? 'Chi tiết video'}>
      {!detail || !v ? <Spin /> : (
        <Space direction="vertical" size={20} style={{ width: '100%' }}>
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="Kênh">{v.channel_title ?? '—'}</Descriptions.Item>
            <Descriptions.Item label="Ngày đăng">{when(v.published_at)}</Descriptions.Item>
            <Descriptions.Item label="Lượt xem">{num(v.view_count)}</Descriptions.Item>
            <Descriptions.Item label="Lượt thích">{num(v.like_count)}</Descriptions.Item>
            <Descriptions.Item label="Bình luận (YouTube)">{num(v.comment_count)}</Descriptions.Item>
            <Descriptions.Item label="Bình luận đã thu">{num(v.collected_comments)}</Descriptions.Item>
            <Descriptions.Item label="Liên kết" span={2}>
              <Link href={youtubeUrl(v.video_id)} target="_blank">{youtubeUrl(v.video_id)}</Link>
            </Descriptions.Item>
            {detail.tags.length > 0 && (
              <Descriptions.Item label="Tag" span={2}>{detail.tags.map((t) => <Tag key={t}>{t}</Tag>)}</Descriptions.Item>
            )}
          </Descriptions>

          <div>
            <Text strong>Lượt xem và lượt thích theo thời gian</Text>
            {series.length < 2 ? (
              <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>Chưa đủ số liệu (cần ít nhất 2 lần chụp).</Text>
            ) : (
              <div style={{ height: 240, marginTop: 8 }}>
                <ResponsiveContainer>
                  <LineChart data={series}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" fontSize={11} />
                    <YAxis yAxisId="v" fontSize={11} />
                    <YAxis yAxisId="l" orientation="right" fontSize={11} />
                    <RTooltip />
                    <Legend />
                    <Line yAxisId="v" type="monotone" dataKey="views" name="Lượt xem" stroke="#2563eb" dot={false} />
                    <Line yAxisId="l" type="monotone" dataKey="likes" name="Lượt thích" stroke="#dc2626" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div>
            <Text strong>Bình luận nhiều lượt thích nhất</Text>
            <List
              size="small"
              style={{ marginTop: 8 }}
              dataSource={detail.top_comments}
              locale={{ emptyText: 'Chưa thu được bình luận nào' }}
              renderItem={(c) => (
                <List.Item>
                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                    {c.text === null
                      ? <Text type="secondary">(chưa qua bước làm sạch nên chưa hiển thị nội dung)</Text>
                      : <Text>{c.text}</Text>}
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {num(c.like_count)} thích{c.reply_count ? ` · ${c.reply_count} trả lời` : ''}{c.is_reply ? ' · là trả lời' : ''}
                    </Text>
                  </Space>
                </List.Item>
              )}
            />
          </div>
        </Space>
      )}
    </Drawer>
  )
}

export default function VideosTab() {
  const [data, setData] = useState<VideoInfo[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [q, setQ] = useState('')
  const [sort, setSort] = useState('views')
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    api.videos.list({ page, pageSize, q, sort })
      .then((res) => { setData(res.items); setTotal(res.total) })
      .catch(() => message.error('Không tải được danh sách video'))
      .finally(() => setLoading(false))
  }, [page, pageSize, q, sort])

  const columns = [
    {
      title: 'Video',
      dataIndex: 'title',
      key: 'title',
      render: (t: string, r: VideoInfo) => (
        <Space direction="vertical" size={0}>
          <a onClick={() => setSelected(r.video_id)}>{t.length > 90 ? `${t.slice(0, 90)}…` : t}</a>
          <Text type="secondary" style={{ fontSize: 12 }}>{r.channel_title ?? '—'}</Text>
        </Space>
      ),
    },
    { title: 'Lượt xem', dataIndex: 'view_count', key: 'view_count', width: 110, align: 'right' as const, render: num },
    { title: 'Lượt thích', dataIndex: 'like_count', key: 'like_count', width: 110, align: 'right' as const, render: num },
    { title: 'Bình luận', dataIndex: 'comment_count', key: 'comment_count', width: 110, align: 'right' as const, render: num },
    { title: 'Đã thu', dataIndex: 'collected_comments', key: 'collected_comments', width: 90, align: 'right' as const, render: num },
    { title: 'Ngày đăng', dataIndex: 'published_at', key: 'published_at', width: 160, render: when },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          allowClear
          placeholder="Tìm theo tiêu đề hoặc kênh"
          style={{ width: 300 }}
          onSearch={(v) => { setPage(1); setQ(v) }}
        />
        <Select
          value={sort}
          style={{ width: 200 }}
          onChange={(v) => { setPage(1); setSort(v) }}
          options={[
            { value: 'views', label: 'Nhiều lượt xem nhất' },
            { value: 'likes', label: 'Nhiều lượt thích nhất' },
            { value: 'comments', label: 'Nhiều bình luận nhất' },
            { value: 'published', label: 'Mới đăng nhất' },
          ]}
        />
        <Text type="secondary">{total} video · số liệu là lần chụp gần nhất</Text>
      </Space>
      <Table
        rowKey="video_id"
        size="middle"
        loading={loading}
        dataSource={data}
        columns={columns}
        pagination={{ current: page, pageSize, total, showSizeChanger: true, showTotal: (t) => `${t} video` }}
        onChange={(p: TablePaginationConfig) => { setPage(p.current ?? 1); setPageSize(p.pageSize ?? 20) }}
      />
      <VideoDrawer videoId={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
