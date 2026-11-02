import { useEffect, useState } from 'react'
import { Alert, Card, Progress, Select, Space, Spin, Table, Tag, Tooltip, Typography } from 'antd'
import { Line, LineChart, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from 'recharts'
import { api, type TopicInfo, type TopicsResponse } from './api'
import { EmptyHint, SENTIMENT_COLOR, SHIFT_TAG, TREND_TAG, fmtTime } from './ui'

const { Text, Paragraph } = Typography

export default function Trends() {
  const [category, setCategory] = useState<string | undefined>()
  const [data, setData] = useState<TopicsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { api.topics(category).then(setData).catch((e) => setError(e.message)) }, [category])

  if (error) return <Alert type="error" showIcon message={error} />
  if (!data) return <Spin />
  const categories = [...new Set(data.topics.map((t) => t.category).filter(Boolean))] as string[]

  return (
    <Card>
      <Paragraph type="secondary">
        Chủ đề được gom tự động từ các bài 60 ngày gần nhất (TF-IDF + NMF) theo từng chủ đề thu thập. Xu hướng so 3 ngày gần nhất
        với tối đa 7 ngày trước đó: <Tag color="purple">Mới nổi</Tag><Tag color="volcano">Đang tăng</Tag> (≥ +50%)
        <Tag color="blue">Đang giảm</Tag> (≤ −50%) <Tag>Ổn định</Tag>. Chỉ phân tích ở mức cộng đồng, không theo từng người dùng (QD-05).
      </Paragraph>
      <Space style={{ marginBottom: 16 }}>
        <Select allowClear placeholder="Mọi chủ đề thu thập" style={{ width: 240 }} value={category} onChange={setCategory}
          options={(category ? [category] : categories).map((c) => ({ value: c, label: c }))} />
        {data.run && <Text type="secondary">Phân tích lúc {fmtTime(data.run.finished_at)}</Text>}
      </Space>
      {Array.isArray(data.run?.hashtags) && (data.run!.hashtags as unknown[]).length > 0 && (
        <Table size="small" style={{ marginBottom: 16 }} pagination={false} rowKey="hashtag" title={() => 'Hashtag nổi bật (theo số bài 3 ngày gần nhất)'}
          dataSource={data.run!.hashtags as { hashtag: string; total: number; recent: number; trend_label: string; growth: number; category: string }[]}
          columns={[
            { title: 'Hashtag', dataIndex: 'hashtag', render: (v) => <Tag color="blue">{v}</Tag> },
            { title: 'Chủ đề thu thập', dataIndex: 'category' },
            { title: '3 ngày gần nhất', dataIndex: 'recent', align: 'right' },
            { title: 'Tổng', dataIndex: 'total', align: 'right' },
            { title: 'Xu hướng', dataIndex: 'trend_label', render: (v) => <Tag color={TREND_TAG[v]}>{v}</Tag> },
          ]} />
      )}
      {!data.topics.length ? (
        <EmptyHint>
          {data.run ? String(data.run.note ?? 'Chưa đủ dữ liệu để gom chủ đề.') : 'Chưa chạy phân tích xu hướng.'}
          <br />Cần ít nhất 20 bài/chủ đề thu thập, trải trên ≥ 2 ngày để phân loại xu hướng. Chạy bước <b>Xu hướng</b> ở mục Pipeline.
        </EmptyHint>
      ) : (
        <Table<TopicInfo>
          rowKey="id" dataSource={data.topics} pagination={false} size="middle"
          columns={[
            { title: 'Chủ đề thu thập', dataIndex: 'category', width: 150, render: (v) => <Tag>{v}</Tag> },
            { title: 'Từ khóa đại diện', dataIndex: 'keywords', render: (v: string) => v.split(', ').map((k) => <Tag key={k} bordered={false} color="blue">{k}</Tag>) },
            { title: 'Số bài', dataIndex: 'size', width: 80, align: 'right' },
            { title: 'Xu hướng', dataIndex: 'trend_label', width: 150, render: (v, r) => (
              <Space size={4}><Tag color={TREND_TAG[v]}>{v}</Tag>{v !== 'Chưa đủ dữ liệu' && v !== 'Mới nổi' ? <Text type="secondary">{r.growth > 0 ? '+' : ''}{Math.round(r.growth * 100)}%</Text> : null}</Space>
            ) },
            { title: 'Chiều cảm xúc', dataIndex: 'sentiment_shift', width: 130, render: (v) => <Tag color={SHIFT_TAG[v]}>{v}</Tag> },
            { title: 'Tích cực / Tiêu cực', width: 180, render: (_, r) => (
              <Tooltip title={`Tích cực ${Math.round(r.positive_share * 100)}% · Trung tính ${Math.round(r.neutral_share * 100)}% · Tiêu cực ${Math.round(r.negative_share * 100)}%`}>
                <Progress percent={Math.round((r.positive_share + r.negative_share) * 100)} success={{ percent: Math.round(r.positive_share * 100), strokeColor: SENTIMENT_COLOR['Tích cực'] }}
                  strokeColor={SENTIMENT_COLOR['Tiêu cực']} showInfo={false} size="small" />
              </Tooltip>
            ) },
            { title: 'Độ quan tâm theo ngày', width: 200, render: (_, r) => (
              <ResponsiveContainer width="100%" height={40}>
                <LineChart data={r.daily}><XAxis dataKey="day" hide /><YAxis hide /><RTooltip /><Line type="monotone" dataKey="count" name="Số bài" stroke="#2563eb" dot={false} /></LineChart>
              </ResponsiveContainer>
            ) },
          ]}
        />
      )}
    </Card>
  )
}
