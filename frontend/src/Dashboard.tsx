import { useEffect, useMemo, useState } from 'react'
import { Alert, Card, Col, Row, Segmented, Select, Space, Spin, Statistic, Typography } from 'antd'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, type DashboardSummary } from './api'
import { EMOTION_COLOR, EMOTION_ORDER, EmptyHint, SENTIMENT_COLOR, SENTIMENT_ORDER, fmtTime, pct } from './ui'

const { Text } = Typography

export default function Dashboard() {
  const [days, setDays] = useState(30)
  const [category, setCategory] = useState<string | undefined>()
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setError(null)
    api.dashboard(days, category).then(setData).catch((e) => setError(e.message))
  }, [days, category])

  const daily = useMemo(() => pivot(data?.series.sentiment ?? []), [data])
  const byCategory = useMemo(() => {
    const m: Record<string, Record<string, number | string>> = {}
    for (const r of data?.by_category ?? []) (m[r.category] ??= { category: r.category })[r.label] = r.count
    return Object.values(m).sort((a, b) => total(b) - total(a)).slice(0, 10)
  }, [data])

  if (error) return <Alert type="error" showIcon message="Không tải được số liệu" description={error} />
  if (!data) return <Spin />
  const t = data.totals
  const alerts = (data.monitor?.alerts as string[] | undefined) ?? []
  const noData = !t.raw

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space wrap>
        <Segmented value={days} onChange={(v) => setDays(v as number)} options={[{ label: '7 ngày', value: 7 }, { label: '30 ngày', value: 30 }, { label: '90 ngày', value: 90 }, { label: '1 năm', value: 365 }]} />
        <Select allowClear placeholder="Mọi chủ đề thu thập" style={{ width: 240 }} value={category} onChange={setCategory}
          options={data.categories.map((c) => ({ value: c, label: c }))} />
      </Space>

      {alerts.length > 0 && <Alert type="warning" showIcon message="Cảnh báo giám sát" description={<ul style={{ margin: 0, paddingLeft: 18 }}>{alerts.map((a) => <li key={a}>{a}</li>)}</ul>} />}

      <Row gutter={[16, 16]}>
        <Col xs={12} lg={6}><Card><Statistic title="Bài thu thập" value={t.raw} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="Dùng được để phân tích" value={t.usable} suffix={t.clean ? <Text type="secondary" style={{ fontSize: 14 }}>/ {t.clean} đã làm sạch</Text> : null} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="Đã gán quan điểm" value={t.analyzed_sentiment ?? 0} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="Đã gán cảm xúc" value={t.analyzed_emotion ?? 0} /></Card></Col>
      </Row>

      <Card size="small">
        <Space wrap size={24}>
          {(['sentiment', 'emotion'] as const).map((k) => {
            const m = data.models[k]
            return <Text key={k}><Text type="secondary">{k === 'sentiment' ? 'Mô hình quan điểm' : 'Mô hình cảm xúc'}: </Text>
              {m ? <>{m.model_name} · F1-macro {pct(m.f1_macro)}</> : <Text type="warning">chưa có</Text>}</Text>
          })}
          <Text type="secondary">Giám sát lần cuối: {fmtTime(data.monitor?.at as string | undefined)}</Text>
        </Space>
      </Card>

      {noData ? (
        <Card><EmptyHint>Chưa có bài thu thập trong khoảng thời gian này. Cấu hình từ khóa ở mục <b>Thu thập</b> (cần YouTube API key trong .env), rồi chạy <b>Pipeline</b>.</EmptyHint></Card>
      ) : (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={10}>
              <Card title="Phân bố quan điểm" size="small"><Distribution counts={data.distribution.sentiment} order={SENTIMENT_ORDER} colors={SENTIMENT_COLOR} /></Card>
            </Col>
            <Col xs={24} lg={14}>
              <Card title="Phân bố cảm xúc" size="small"><Distribution counts={data.distribution.emotion} order={EMOTION_ORDER} colors={EMOTION_COLOR} /></Card>
            </Col>
          </Row>
          <Card title="Quan điểm theo ngày" size="small">
            {daily.length ? (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
                  <XAxis dataKey="day" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                  <Tooltip /><Legend />
                  {SENTIMENT_ORDER.map((l) => <Area key={l} type="monotone" dataKey={l} stackId="1" stroke={SENTIMENT_COLOR[l]} fill={SENTIMENT_COLOR[l]} fillOpacity={0.35} />)}
                </AreaChart>
              </ResponsiveContainer>
            ) : <EmptyHint>Chưa có bài được gán nhãn - chạy bước Dự đoán ở mục Pipeline.</EmptyHint>}
          </Card>
          <Card title="Quan điểm theo chủ đề thu thập (10 chủ đề nhiều bài nhất)" size="small">
            {byCategory.length ? (
              <ResponsiveContainer width="100%" height={Math.max(160, byCategory.length * 36)}>
                <BarChart data={byCategory} layout="vertical" margin={{ left: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
                  <XAxis type="number" tick={{ fontSize: 12 }} allowDecimals={false} /><YAxis type="category" dataKey="category" width={160} tick={{ fontSize: 12 }} />
                  <Tooltip /><Legend />
                  {SENTIMENT_ORDER.map((l) => <Bar key={l} dataKey={l} stackId="a" fill={SENTIMENT_COLOR[l]} />)}
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyHint>Chưa có dữ liệu.</EmptyHint>}
          </Card>
        </>
      )}
    </Space>
  )
}

function total(r: Record<string, number | string>) {
  return Object.values(r).reduce<number>((s, v) => s + (typeof v === 'number' ? v : 0), 0)
}

function pivot(rows: { day: string; label: string; count: number }[]) {
  const m: Record<string, Record<string, number | string>> = {}
  for (const r of rows) (m[r.day] ??= { day: r.day })[r.label] = r.count
  return Object.values(m)
}

function Distribution({ counts, order, colors }: { counts: Record<string, number>; order: string[]; colors: Record<string, string> }) {
  const sum = Object.values(counts).reduce((a, b) => a + b, 0)
  if (!sum) return <EmptyHint>Chưa có bài được gán nhãn.</EmptyHint>
  const rows = order.filter((l) => counts[l]).map((l) => ({ label: l, count: counts[l], share: counts[l] / sum }))
  return (
    <ResponsiveContainer width="100%" height={Math.max(140, rows.length * 34)}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 48 }}>
        <XAxis type="number" hide /><YAxis type="category" dataKey="label" width={90} tick={{ fontSize: 13 }} />
        <Tooltip formatter={(v) => [`${v} bài (${pct(Number(v) / sum)})`, 'Số bài']} />
        <Bar dataKey="count" radius={[0, 4, 4, 0]} label={{ position: 'right', fontSize: 12, formatter: (v) => pct(Number(v) / sum) }}>
          {rows.map((r) => <Cell key={r.label} fill={colors[r.label]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
