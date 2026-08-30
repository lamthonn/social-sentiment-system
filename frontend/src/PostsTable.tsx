import { useEffect, useState } from 'react'
import { Select, Space, Table, Tag, Typography, message } from 'antd'
import type { TablePaginationConfig } from 'antd/es/table'
import { api, type RawPost } from './api'

const { Text } = Typography

function formatDateTime(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('vi-VN')
}

export default function PostsTable() {
  const [data, setData] = useState<RawPost[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [platform, setPlatform] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api
      .posts({ page, pageSize, platform })
      .then((res) => {
        setData(res.items)
        setTotal(res.total)
      })
      .catch(() => message.error('Không tải được dữ liệu bài đăng - kiểm tra API/kết nối DB'))
      .finally(() => setLoading(false))
  }, [page, pageSize, platform])

  const columns = [
    {
      title: 'Nền tảng',
      dataIndex: 'platform',
      key: 'platform',
      width: 100,
      render: (value: string) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: 'Nội dung',
      dataIndex: 'content',
      key: 'content',
      render: (value: string) => <Text>{value.length > 160 ? `${value.slice(0, 160)}…` : value}</Text>,
    },
    {
      title: 'Tác giả (hash)',
      dataIndex: 'author_hash',
      key: 'author_hash',
      width: 130,
      render: (value: string) => <Text code>{value.slice(0, 10)}…</Text>,
    },
    {
      title: 'Đăng lúc',
      dataIndex: 'posted_at',
      key: 'posted_at',
      width: 170,
      render: formatDateTime,
    },
    {
      title: 'Thu thập lúc',
      dataIndex: 'collected_at',
      key: 'collected_at',
      width: 170,
      render: formatDateTime,
    },
  ]

  const pagination: TablePaginationConfig = {
    current: page,
    pageSize,
    total,
    showSizeChanger: true,
    showTotal: (t) => `${t} bài`,
    onChange: (newPage, newPageSize) => {
      setPage(newPage)
      setPageSize(newPageSize)
    },
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Text>Lọc nền tảng:</Text>
        <Select
          allowClear
          style={{ width: 160 }}
          placeholder="Tất cả"
          value={platform}
          onChange={setPlatform}
          options={[{ value: 'youtube', label: 'YouTube' }]}
        />
      </Space>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={pagination}
        scroll={{ x: true }}
      />
    </div>
  )
}
