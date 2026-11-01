import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Checkbox, Form, Input, Modal, Select, Space, Switch, Table, Tabs, Tag, message } from 'antd'
import { api, ROLE_LABEL, type AuditItem, type Role, type UserInfo } from './api'
import { fmtTime } from './ui'

const ROLE_OPTIONS = (Object.keys(ROLE_LABEL) as Role[]).map((r) => ({ value: r, label: ROLE_LABEL[r] }))

export default function Admin({ me }: { me: string }) {
  return <Tabs items={[
    { key: 'users', label: 'Người dùng', children: <Users me={me} /> },
    { key: 'audit', label: 'Nhật ký truy cập', children: <Audit /> },
  ]} />
}

function Users({ me }: { me: string }) {
  const [users, setUsers] = useState<UserInfo[]>([])
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()
  const load = () => api.users.list().then(setUsers).catch((e) => message.error(e.message))
  useEffect(() => { load() }, [])

  const update = async (id: number, body: Partial<{ role: Role; is_active: boolean; password: string }>) => {
    try { await api.users.update(id, body); message.success('Đã cập nhật'); load() } catch (e) { message.error((e as Error).message) }
  }
  const create = async () => {
    const v = await form.validateFields()
    try { await api.users.create(v); message.success('Đã tạo tài khoản'); setOpen(false); form.resetFields(); load() } catch (e) { message.error((e as Error).message) }
  }
  const resetPassword = (u: UserInfo) => {
    let pw = ''
    Modal.confirm({
      title: `Đặt mật khẩu mới cho ${u.username}`, okText: 'Lưu', cancelText: 'Hủy',
      content: <Input.Password placeholder="≥ 10 ký tự, có chữ và số" onChange={(e) => { pw = e.target.value }} />,
      onOk: () => update(u.id, { password: pw }),
    })
  }

  return (
    <Card extra={<Button type="primary" onClick={() => setOpen(true)}>Thêm tài khoản</Button>}>
      <Table<UserInfo> rowKey="id" dataSource={users} pagination={false} columns={[
        { title: 'Tên đăng nhập', dataIndex: 'username', render: (v) => <>{v}{v === me && <Tag style={{ marginLeft: 6 }}>bạn</Tag>}</> },
        { title: 'Vai trò', dataIndex: 'role', render: (v: Role, u) => <Select value={v} options={ROLE_OPTIONS} style={{ width: 160 }} disabled={u.username === me} onChange={(role) => update(u.id, { role })} /> },
        { title: 'Hoạt động', dataIndex: 'is_active', render: (v: boolean, u) => <Switch checked={v} disabled={u.username === me} onChange={(is_active) => update(u.id, { is_active })} /> },
        { title: 'Tạo lúc', dataIndex: 'created_at', render: fmtTime },
        { title: '', render: (_, u) => <Button size="small" onClick={() => resetPassword(u)}>Đặt lại mật khẩu</Button> },
      ]} />
      <Modal title="Thêm tài khoản" open={open} onOk={create} onCancel={() => setOpen(false)} okText="Tạo" cancelText="Hủy">
        <Form form={form} layout="vertical" initialValues={{ role: 'viewer' }}>
          <Form.Item name="username" label="Tên đăng nhập" rules={[{ required: true, pattern: /^[a-z0-9._-]{3,32}$/, message: '3–32 ký tự a-z, 0-9, . _ -' }]}><Input /></Form.Item>
          <Form.Item name="password" label="Mật khẩu (≥ 10 ký tự, có chữ và số)" rules={[{ required: true, min: 10 }]}><Input.Password /></Form.Item>
          <Form.Item name="role" label="Vai trò"><Select options={ROLE_OPTIONS} /></Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

function Audit() {
  const [q, setQ] = useState<{ page: number; username?: string; action?: string; failed_only?: boolean }>({ page: 1 })
  const [data, setData] = useState<{ items: AuditItem[]; total: number }>({ items: [], total: 0 })
  const load = useCallback(() => api.audit(q).then(setData).catch((e) => message.error(e.message)), [q])
  useEffect(() => { load() }, [load])

  return (
    <Card>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input.Search placeholder="Tên đăng nhập" allowClear style={{ width: 180 }} onSearch={(v) => setQ({ ...q, page: 1, username: v || undefined })} />
        <Input.Search placeholder="Thao tác (vd: login)" allowClear style={{ width: 200 }} onSearch={(v) => setQ({ ...q, page: 1, action: v || undefined })} />
        <Checkbox onChange={(e) => setQ({ ...q, page: 1, failed_only: e.target.checked || undefined })}>Chỉ thao tác thất bại / bị từ chối</Checkbox>
      </Space>
      <Table<AuditItem> rowKey="id" dataSource={data.items} size="small"
        pagination={{ current: q.page, pageSize: 50, total: data.total, onChange: (page) => setQ({ ...q, page }) }}
        columns={[
          { title: 'Thời gian', dataIndex: 'at', width: 170, render: fmtTime },
          { title: 'Người dùng', dataIndex: 'username', width: 130 },
          { title: 'Thao tác', dataIndex: 'action', width: 160 },
          { title: 'Chi tiết', dataIndex: 'detail' },
          { title: 'IP', dataIndex: 'ip', width: 120 },
          { title: 'Kết quả', dataIndex: 'success', width: 100, render: (v) => (v ? <Tag color="green">OK</Tag> : <Tag color="red">Thất bại</Tag>) },
        ]} />
    </Card>
  )
}
