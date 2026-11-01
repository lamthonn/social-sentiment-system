import { useCallback, useEffect, useState } from 'react'
import { Button, Card, InputNumber, Select, Space, Steps, Table, Tag, Typography, message } from 'antd'
import { api, type PipelineRunInfo, type PipelineRunsResponse, type Role } from './api'
import { RUN_STATUS, STEP_LABEL, fmtTime } from './ui'

const { Text, Paragraph } = Typography
const FLOW = [
  { step: 'collect', title: 'Thu thập', desc: 'PL-01' }, { step: 'clean', title: 'Làm sạch', desc: 'PL-02' },
  { step: 'predict', title: 'Dự đoán', desc: 'PL-07' }, { step: 'trends', title: 'Xu hướng', desc: 'PL-07' },
  { step: 'monitor', title: 'Giám sát', desc: 'PL-08' },
]

export default function Pipeline({ role }: { role: Role }) {
  const [data, setData] = useState<PipelineRunsResponse | null>(null)
  const [page, setPage] = useState(1)
  const [train, setTrain] = useState({ task: 'sentiment', model: 'tfidf-lr', epochs: 4 })
  const load = useCallback(() => api.pipelineRuns(page).then(setData).catch((e) => message.error(e.message)), [page])

  useEffect(() => { load() }, [load])
  useEffect(() => { // tự làm mới khi có bước đang chạy
    const running = data?.running.length || data?.items.some((r) => r.status === 'running')
    if (!running) return
    const t = setInterval(load, 4000)
    return () => clearInterval(t)
  }, [data, load])

  const run = async (body: { step: string; task?: string; model?: string; epochs?: number }) => {
    try {
      await api.runStep(body)
      message.success(`Đã bắt đầu: ${STEP_LABEL[body.step] ?? body.step}`)
      setTimeout(load, 800)
    } catch (e) { message.error((e as Error).message) }
  }
  const lastStatus = (step: string) => data?.items.find((r) => r.step === step)?.status
  const busy = (step: string) => data?.running.includes(step)

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card title="Chuỗi xử lý dữ liệu thu thập" size="small"
        extra={<Button type="primary" onClick={() => run({ step: 'run' })} loading={busy('run')}>Chạy cả chuỗi</Button>}>
        <Steps size="small" items={FLOW.map((f) => {
          const st = lastStatus(f.step)
          return { title: f.title, description: <>{f.desc}<br /><Button size="small" style={{ marginTop: 6 }} loading={busy(f.step)} onClick={() => run({ step: f.step })}>Chạy</Button></>,
            status: st === 'failed' ? 'error' : st === 'success' ? 'finish' : st === 'running' ? 'process' : 'wait' }
        })} />
        <Paragraph type="secondary" style={{ margin: '12px 0 0' }}>
          Thu thập cần YouTube API key trong <Text code>.env</Text>; nếu chưa có, bước này được ghi là "Bỏ qua". Thu thập tự động định kỳ bật ở mục Thu thập › Cấu hình.
        </Paragraph>
      </Card>

      {role === 'admin' && (
        <Card title="Dữ liệu huấn luyện và mô hình (chỉ quản trị)" size="small">
          <Space wrap>
            <Button onClick={() => run({ step: 'datasets' })} loading={busy('datasets')}>Chuẩn bị dataset (UIT-VSFC, UIT-VSMEC)</Button>
            <Text type="secondary">Huấn luyện:</Text>
            <Select value={train.task} style={{ width: 200 }} onChange={(task) => setTrain({ ...train, task })}
              options={[{ value: 'sentiment', label: 'Quan điểm 3 lớp' }, { value: 'emotion', label: 'Cảm xúc 7 nhãn' }]} />
            <Select value={train.model} style={{ width: 230 }} onChange={(model) => setTrain({ ...train, model })}
              options={[{ value: 'tfidf-lr', label: 'TF-IDF + Logistic Regression' }, { value: 'tfidf-svm', label: 'TF-IDF + Linear SVM' }, { value: 'bilstm', label: 'BiLSTM (vài phút)' },
                { value: 'visobert', label: 'ViSoBERT (GPU, vài chục phút)' }, { value: 'phobert', label: 'PhoBERT-base-v2 (GPU, vài chục phút)' }]} />
            {['visobert', 'phobert'].includes(train.model) &&<InputNumber min={1} max={10} value={train.epochs} addonAfter="epoch" onChange={(v) => setTrain({ ...train, epochs: v ?? 4 })} />}
            <Button type="primary" loading={busy('train')} onClick={() => run({ step: 'train', ...train })}>Huấn luyện</Button>
          </Space>
        </Card>
      )}

      <Card title="Lịch sử chạy" size="small">
        <Table<PipelineRunInfo>
          rowKey="id" dataSource={data?.items} loading={!data} size="middle"
          pagination={{ current: page, pageSize: 30, total: data?.total, onChange: setPage }}
          expandable={{ expandedRowRender: (r) => <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}>{typeof r.info === 'string' ? r.info : JSON.stringify(r.info, null, 2)}</pre> }}
          columns={[
            { title: '#', dataIndex: 'id', width: 60 },
            { title: 'Bước', dataIndex: 'step', render: (v) => STEP_LABEL[v] ?? v },
            { title: 'Trạng thái', dataIndex: 'status', render: (v) => <Tag color={RUN_STATUS[v]?.color}>{RUN_STATUS[v]?.label ?? v}</Tag> },
            { title: 'Bắt đầu', dataIndex: 'started_at', render: fmtTime },
            { title: 'Thời lượng', render: (_, r) => (r.finished_at ? `${Math.max(0, Math.round((+new Date(r.finished_at + 'Z') - +new Date(r.started_at + 'Z')) / 1000))} giây` : '…') },
            { title: 'Vào → ra', render: (_, r) => `${r.records_in} → ${r.records_out}` },
            { title: 'Người chạy', dataIndex: 'triggered_by' },
          ]}
        />
      </Card>
    </Space>
  )
}
