import { useEffect, useState } from 'react'
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import {
  api,
  type SchedulerStatus,
  type SearchQuery,
  type SearchQueryInput,
  type TrackedVideo,
  type TrackedVideoInput,
} from './api'

const { Title, Text } = Typography

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback
}

function SchedulerPanel() {
  const [status, setStatus] = useState<SchedulerStatus | null>(null)
  const [toggling, setToggling] = useState(false)

  const load = () => {
    api.scheduler
      .status()
      .then(setStatus)
      .catch(() => message.error('Không tải được trạng thái thu thập tự động'))
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 30_000)
    return () => clearInterval(timer)
  }, [])

  const handleToggle = async (enabled: boolean) => {
    setToggling(true)
    try {
      setStatus(await api.scheduler.toggle(enabled))
      message.success(enabled ? 'Đã bật thu thập tự động' : 'Đã tắt thu thập tự động')
    } catch (err) {
      message.error(errorMessage(err, 'Cập nhật thất bại'))
    } finally {
      setToggling(false)
    }
  }

  return (
    <Card style={{ marginBottom: 32 }}>
      <Space align="start" size="middle">
        <Switch checked={status?.enabled ?? false} loading={toggling || !status} onChange={handleToggle} />
        <div>
          <Space>
            <Text strong>Thu thập tự động</Text>
            <Tag color={status?.enabled ? 'success' : 'default'}>{status?.enabled ? 'Đang bật' : 'Đang tắt'}</Tag>
          </Space>
          {status && (
            <div>
              <Text type="secondary">
                Chu kỳ mỗi {status.poll_interval_minutes} phút
                {status.enabled && status.next_run_at &&
                  ` — lượt kế tiếp lúc ${new Date(status.next_run_at).toLocaleString('vi-VN')}`}
              </Text>
            </div>
          )}
        </div>
      </Space>
    </Card>
  )
}

function SearchQueriesPanel() {
  const [data, setData] = useState<SearchQuery[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<SearchQuery | null>(null)
  const [form] = Form.useForm<SearchQueryInput>()

  const load = () => {
    setLoading(true)
    api.searchQueries
      .list()
      .then(setData)
      .catch(() => message.error('Không tải được danh sách từ khóa'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (row: SearchQuery) => {
    setEditing(row)
    form.setFieldsValue(row)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    try {
      if (editing) {
        await api.searchQueries.update(editing.id, values)
      } else {
        await api.searchQueries.create(values)
      }
      setModalOpen(false)
      load()
    } catch (err) {
      message.error(errorMessage(err, 'Lưu thất bại'))
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.searchQueries.remove(id)
      load()
    } catch {
      message.error('Xóa thất bại')
    }
  }

  const handleToggleEnabled = async (row: SearchQuery, enabled: boolean) => {
    try {
      const { id: _id, created_at: _createdAt, ...rest } = row
      await api.searchQueries.update(row.id, { ...rest, enabled })
      load()
    } catch {
      message.error('Cập nhật thất bại')
    }
  }

  const columns = [
    { title: 'Từ khóa', dataIndex: 'query', key: 'query' },
    {
      title: 'Nền tảng', dataIndex: 'platform', key: 'platform', width: 100,
      render: (value: string) => <Tag color="red">{value}</Tag>,
    },
    { title: 'Số video tối đa/lượt', dataIndex: 'max_videos', key: 'max_videos', width: 150 },
    { title: 'Trong N ngày gần đây', dataIndex: 'published_within_days', key: 'published_within_days', width: 150 },
    {
      title: 'Bật', dataIndex: 'enabled', key: 'enabled', width: 80,
      render: (value: boolean, row: SearchQuery) => (
        <Switch checked={value} onChange={(checked) => handleToggleEnabled(row, checked)} />
      ),
    },
    {
      title: '', key: 'actions', width: 140,
      render: (_: unknown, row: SearchQuery) => (
        <Space>
          <Button size="small" onClick={() => openEdit(row)}>Sửa</Button>
          <Popconfirm title="Xóa từ khóa này?" onConfirm={() => handleDelete(row.id)}>
            <Button size="small" danger>Xóa</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          Thêm từ khóa
        </Button>
      </Space>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={false} scroll={{ x: true }} />
      <Modal
        title={editing ? 'Sửa từ khóa' : 'Thêm từ khóa'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ platform: 'youtube', max_videos: 10, published_within_days: 7, enabled: true }}
        >
          <Form.Item name="query" label="Từ khóa" rules={[{ required: true, message: 'Nhập từ khóa' }]}>
            <Input placeholder='VD: "giá vàng"' />
          </Form.Item>
          <Form.Item name="platform" label="Nền tảng" rules={[{ required: true }]}>
            <Select disabled options={[{ value: 'youtube', label: 'YouTube (hiện chỉ hỗ trợ tìm theo từ khóa cho YouTube)' }]} />
          </Form.Item>
          <Form.Item name="max_videos" label="Số video tối đa/lượt" rules={[{ required: true }]}>
            <InputNumber min={1} max={50} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="published_within_days"
            label="Chỉ lấy video đăng trong N ngày gần đây"
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={90} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="enabled" label="Bật" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

function TrackedVideosPanel() {
  const [data, setData] = useState<TrackedVideo[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<TrackedVideo | null>(null)
  const [form] = Form.useForm<TrackedVideoInput>()

  const load = () => {
    setLoading(true)
    api.trackedVideos
      .list()
      .then(setData)
      .catch(() => message.error('Không tải được danh sách video'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (row: TrackedVideo) => {
    setEditing(row)
    form.setFieldsValue(row)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    try {
      if (editing) {
        await api.trackedVideos.update(editing.id, values)
      } else {
        await api.trackedVideos.create(values)
      }
      setModalOpen(false)
      load()
    } catch (err) {
      message.error(errorMessage(err, 'Lưu thất bại'))
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.trackedVideos.remove(id)
      load()
    } catch {
      message.error('Xóa thất bại')
    }
  }

  const handleToggleEnabled = async (row: TrackedVideo, enabled: boolean) => {
    try {
      await api.trackedVideos.update(row.id, {
        platform: row.platform,
        video_id: row.video_id,
        label: row.label,
        enabled,
      })
      load()
    } catch {
      message.error('Cập nhật thất bại')
    }
  }

  const columns = [
    {
      title: 'Nền tảng', dataIndex: 'platform', key: 'platform', width: 100,
      render: (value: string) => <Tag color={value === 'youtube' ? 'red' : 'geekblue'}>{value}</Tag>,
    },
    { title: 'Video ID', dataIndex: 'video_id', key: 'video_id' },
    {
      title: 'Ghi chú', dataIndex: 'label', key: 'label',
      render: (value: string | null) => value || <Text type="secondary">—</Text>,
    },
    {
      title: 'Bật', dataIndex: 'enabled', key: 'enabled', width: 80,
      render: (value: boolean, row: TrackedVideo) => (
        <Switch checked={value} onChange={(checked) => handleToggleEnabled(row, checked)} />
      ),
    },
    {
      title: '', key: 'actions', width: 140,
      render: (_: unknown, row: TrackedVideo) => (
        <Space>
          <Button size="small" onClick={() => openEdit(row)}>Sửa</Button>
          <Popconfirm title="Xóa video này?" onConfirm={() => handleDelete(row.id)}>
            <Button size="small" danger>Xóa</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          Thêm video
        </Button>
      </Space>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={false} scroll={{ x: true }} />
      <Modal
        title={editing ? 'Sửa video theo dõi' : 'Thêm video theo dõi'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        destroyOnClose
      >
        <Form form={form} layout="vertical" initialValues={{ platform: 'youtube', enabled: true }}>
          <Form.Item name="platform" label="Nền tảng" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'youtube', label: 'YouTube' },
                { value: 'tiktok', label: 'TikTok' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="video_id"
            label="Video ID hoặc URL"
            rules={[{ required: true, message: 'Nhập video ID hoặc dán URL' }]}
          >
            <Input placeholder="Dán URL đầy đủ hoặc chỉ ID cũng được" />
          </Form.Item>
          <Form.Item name="label" label="Ghi chú (tùy chọn)">
            <Input placeholder="VD: Video phát biểu ngày 1/1" />
          </Form.Item>
          <Form.Item name="enabled" label="Bật" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default function CollectorConfig() {
  return (
    <div>
      <SchedulerPanel />

      <Title level={5}>Từ khóa tìm kiếm (YouTube)</Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        Tự động tìm video mới khớp từ khóa mỗi lượt chạy scheduler - chỉ tìm video đăng trong
        khoảng ngày cấu hình, chỉ hỗ trợ YouTube.
      </Text>
      <SearchQueriesPanel />

      <Title level={5} style={{ marginTop: 32 }}>Video theo dõi cố định</Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        Theo dõi liên tục 1 video cụ thể (YouTube hoặc TikTok) - không giới hạn thời gian như
        tìm theo từ khóa, phù hợp khi đã biết chính xác video cần theo dõi lâu dài.
      </Text>
      <TrackedVideosPanel />
    </div>
  )
}
