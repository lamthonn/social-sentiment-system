import { useEffect, useState } from 'react'
import { Alert, Button, Card, Collapse, Descriptions, Popconfirm, Space, Spin, Table, Tag, Typography, message } from 'antd'
import { api, type ExperimentInfo, type ModelRunInfo } from './api'
import { TASK_LABEL, fmtTime, pct } from './ui'

const { Text, Paragraph } = Typography

export default function Models({ isAdmin }: { isAdmin: boolean }) {
  const [runs, setRuns] = useState<ModelRunInfo[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const load = () => api.modelRuns().then(setRuns).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const choose = async (r: ModelRunInfo) => {
    try {
      await api.selectModel(r.id)
      message.success(`Đã chọn ${r.model_name} cho ${TASK_LABEL[r.task]}`)
      load()
    } catch (e) { message.error((e as Error).message) }
  }

  if (error) return <Alert type="error" showIcon message={error} />
  if (!runs) return <Spin />

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Paragraph type="secondary" style={{ margin: 0 }}>
        Mỗi dòng là một lần huấn luyện, đánh giá trên tập test của bộ dữ liệu. Chỉ số chính là <b>F1-macro</b> (dữ liệu lệch lớp mạnh).
        Mô hình <Tag color="green">đang dùng</Tag> là mô hình gán nhãn cho dữ liệu thu thập ở bước Dự đoán.
      </Paragraph>
      {(['sentiment', 'emotion'] as const).map((task) => {
        const list = runs.filter((r) => r.task === task)
        const best = Math.max(...list.map((r) => r.f1_macro))
        return (
          <Card key={task} title={TASK_LABEL[task]} size="small">
            <Table<ModelRunInfo>
              rowKey="id" dataSource={list} pagination={false} size="middle"
              expandable={{ expandedRowRender: (r) => <RunDetail r={r} /> }}
              columns={[
                { title: 'Mô hình', dataIndex: 'model_name', render: (v, r) => <Space>{v}{r.selected && <Tag color="green">đang dùng</Tag>}</Space> },
                { title: 'Accuracy', dataIndex: 'accuracy', align: 'right', render: pct },
                { title: 'F1-macro', dataIndex: 'f1_macro', align: 'right', render: (v: number) => <Text strong={v === best}>{pct(v)}</Text> },
                { title: 'Precision', dataIndex: 'precision_macro', align: 'right', render: pct },
                { title: 'Recall', dataIndex: 'recall_macro', align: 'right', render: pct },
                { title: 'Thời gian huấn luyện', dataIndex: 'train_seconds', align: 'right', render: (v: number) => (v >= 120 ? `${Math.round(v / 60)} phút` : `${Math.round(v)} giây`) },
                { title: 'Ngày chạy', dataIndex: 'created_at', render: fmtTime },
                ...(isAdmin ? [{ title: '', width: 110, render: (_: unknown, r: ModelRunInfo) => (r.selected ? null : (
                  <Popconfirm title="Dùng mô hình này để gán nhãn dữ liệu mới?" onConfirm={() => choose(r)} okText="Chọn" cancelText="Hủy">
                    <Button size="small">Chọn dùng</Button>
                  </Popconfirm>
                )) }] : []),
              ]}
            />
          </Card>
        )
      })}
      <Experiments />
    </Space>
  )
}

// Thực nghiệm bổ sung (python -m experiments.<tên>): đầu độc dữ liệu, độ bền, DP-SGD, gom chủ đề, LLM, hiệu năng
const ORDER = ['robustness', 'llm', 'topics_eval', 'dp', 'poisoning', 'perf']
function Experiments() {
  const [items, setItems] = useState<ExperimentInfo[] | null>(null)
  useEffect(() => { api.experiments().then(setItems).catch(() => setItems([])) }, [])
  if (!items) return <Spin />
  if (!items.length) return null
  const sorted = [...items].sort((a, b) => ORDER.indexOf(a.name) - ORDER.indexOf(b.name))
  return (
    <Card title="Thực nghiệm bổ sung" size="small">
      <Collapse defaultActiveKey={[sorted[0].name]} items={sorted.map((e) => ({
        key: e.name,
        label: <Space wrap><b>{e.title}</b><Tag color="blue">{e.question}</Tag><Text type="secondary">{fmtTime(e.created_at)}</Text></Space>,
        children: (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Paragraph type="secondary" style={{ margin: 0 }}>{e.description}</Paragraph>
            <Alert type="info" showIcon message="Kết quả chính" description={<ul style={{ margin: 0, paddingLeft: 18 }}>{e.findings.map((f) => <li key={f}>{f}</li>)}</ul>} />
            {e.tables.map((t) => (
              <Table key={t.title} size="small" pagination={false} title={() => t.title} scroll={{ x: true }}
                rowKey={(_, i) => String(i)} dataSource={t.rows}
                columns={t.columns.map((c) => ({ title: c, dataIndex: c, render: (v: unknown) => (v === null || v === undefined ? '—' : String(v)) }))} />
            ))}
            <Text type="secondary" style={{ fontSize: 12 }}>Môi trường: {Object.entries(e.env).map(([k, v]) => `${k} ${v}`).join(' · ')}</Text>
          </Space>
        ),
      }))} />
    </Card>
  )
}

function RunDetail({ r }: { r: ModelRunInfo }) {
  const { labels, matrix } = r.confusion
  const history = (r.params.history as { epoch: number; loss: number; val_f1_macro: number }[] | undefined) ?? []
  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Table size="small" pagination={false} rowKey="label" title={() => 'Chỉ số theo lớp (tập test)'}
        dataSource={Object.entries(r.per_class).map(([label, m]) => ({ label, ...m }))}
        columns={[
          { title: 'Nhãn', dataIndex: 'label' }, { title: 'Precision', dataIndex: 'precision', render: pct },
          { title: 'Recall', dataIndex: 'recall', render: pct }, { title: 'F1', dataIndex: 'f1', render: pct }, { title: 'Số mẫu', dataIndex: 'support' },
        ]} />
      <div>
        <Text type="secondary">Ma trận nhầm lẫn (hàng = nhãn thật, cột = dự đoán)</Text>
        <table style={{ borderCollapse: 'collapse', marginTop: 6, fontSize: 12 }}>
          <thead><tr><th />{labels.map((l) => <th key={l} style={{ padding: '2px 8px' }}>{l}</th>)}</tr></thead>
          <tbody>{matrix.map((row, i) => {
            const rowSum = row.reduce((a, b) => a + b, 0) || 1
            return <tr key={labels[i]}><th style={{ textAlign: 'right', padding: '2px 8px' }}>{labels[i]}</th>
              {row.map((v, j) => <td key={j} style={{ padding: '2px 8px', textAlign: 'right', background: `rgba(37,99,235,${(v / rowSum) * 0.6})`, color: v / rowSum > 0.5 ? '#fff' : undefined }}>{v}</td>)}</tr>
          })}</tbody>
        </table>
      </div>
      <Descriptions size="small" column={{ xs: 1, md: 2 }} bordered
        items={[
          { key: 'code', label: 'Mã lần chạy', children: <Text code>{r.run_code}</Text> },
          { key: 'ds', label: 'Dữ liệu', children: `${r.dataset} · phiên bản ${r.dataset_version}` },
          ...Object.entries(r.params).filter(([k]) => k !== 'history').map(([k, v]) => ({ key: k, label: k, children: String(v) })),
          ...(history.length ? [{ key: 'h', label: 'Theo epoch', children: history.map((h) => `#${h.epoch}: loss ${h.loss}, val F1 ${pct(h.val_f1_macro)}`).join(' · ') }] : []),
        ]} />
    </Space>
  )
}
