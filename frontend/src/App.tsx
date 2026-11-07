import { useEffect, useState } from 'react'
import { Button, ConfigProvider, Dropdown, Form, Input, Layout, Menu, Modal, Spin, Tabs, Tag, Typography, message } from 'antd'
import {
  ApiOutlined, AuditOutlined, BarChartOutlined, DatabaseOutlined, ExperimentOutlined, LineChartOutlined,
  LogoutOutlined, RiseOutlined, UserOutlined,
} from '@ant-design/icons'
import viVN from 'antd/locale/vi_VN'
import { api, auth, ROLE_LABEL, type CurrentUser, type Role } from './api'
import Login from './Login'
import Dashboard from './Dashboard'
import AnalysisPosts from './AnalysisPosts'
import Trends from './Trends'
import Models from './Models'
import Pipeline from './Pipeline'
import Admin from './Admin'
import PostsTable from './PostsTable'
import CollectorConfig from './CollectorConfig'

const { Header, Sider, Content } = Layout
const RANK: Record<Role, number> = { viewer: 0, analyst: 1, admin: 2 }

// mỗi màn hình kèm vai trò tối thiểu - khớp với quyền phía API (api/security_mw.py)
const PAGES: { key: string; label: string; icon: React.ReactNode; role: Role }[] = [
  { key: 'dashboard', label: 'Tổng quan', icon: <BarChartOutlined />, role: 'viewer' },
  { key: 'trends', label: 'Xu hướng', icon: <RiseOutlined />, role: 'viewer' },
  { key: 'analysis', label: 'Dữ liệu đã phân tích', icon: <LineChartOutlined />, role: 'analyst' },
  { key: 'collect', label: 'Thu thập', icon: <DatabaseOutlined />, role: 'analyst' },
  { key: 'models', label: 'Mô hình', icon: <ExperimentOutlined />, role: 'viewer' },
  { key: 'pipeline', label: 'Pipeline', icon: <ApiOutlined />, role: 'analyst' },
  { key: 'admin', label: 'Người dùng & nhật ký', icon: <AuditOutlined />, role: 'admin' },
]

export default function App() {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [checking, setChecking] = useState(!!auth.token)
  const [page, setPage] = useState(() => location.hash.slice(1) || 'dashboard')
  const [pwOpen, setPwOpen] = useState(false)

  useEffect(() => {
    if (auth.token) api.me().then(setUser).catch(() => auth.set(null)).finally(() => setChecking(false))
    const onLogout = () => setUser(null)
    const onHash = () => setPage(location.hash.slice(1) || 'dashboard') // nút Back/Forward, link trực tiếp
    window.addEventListener('sss-logout', onLogout)
    window.addEventListener('hashchange', onHash)
    return () => {
      window.removeEventListener('sss-logout', onLogout)
      window.removeEventListener('hashchange', onHash)
    }
  }, [])
  useEffect(() => { if (location.hash.slice(1) !== page) location.hash = page }, [page])

  if (checking) return <Spin style={{ marginTop: '40vh', width: '100%' }} />
  if (!user) return <ConfigProvider locale={viVN}><Login onLogin={setUser} /></ConfigProvider>

  const pages = PAGES.filter((p) => RANK[user.role] >= RANK[p.role])
  const current = pages.find((p) => p.key === page) ?? pages[0]
  const logout = () => { auth.set(null); setUser(null) }

  const content: Record<string, React.ReactNode> = {
    dashboard: <Dashboard />,
    trends: <Trends />,
    analysis: <AnalysisPosts isAdmin={user.role === 'admin'} />,
    // dữ liệu thô chưa che PII -> chỉ quản trị (API /posts cũng chặn ở security_mw)
    collect: <Tabs items={[
      ...(user.role === 'admin' ? [{ key: 'raw', label: 'Dữ liệu thô', children: <PostsTable /> }] : []),
      { key: 'config', label: 'Cấu hình thu thập', children: <CollectorConfig /> },
    ]} />,
    models: <Models isAdmin={user.role === 'admin'} />,
    pipeline: <Pipeline role={user.role} />,
    admin: <Admin me={user.username} />,
  }

  return (
    <ConfigProvider locale={viVN} theme={{ token: { colorPrimary: '#2563eb', borderRadius: 8, fontSize: 14 } }}>
      <Layout style={{ minHeight: '100vh' }}>
        <Sider breakpoint="lg" collapsedWidth={0} theme="light" width={220} style={{ borderRight: '1px solid #eef0f3' }}>
          <div style={{ padding: '18px 20px', fontWeight: 600, lineHeight: 1.3 }}>Cảm xúc & xu hướng<br /><span style={{ fontWeight: 400, color: '#6b7280', fontSize: 12 }}>mạng xã hội tiếng Việt</span></div>
          <Menu mode="inline" selectedKeys={[current.key]} onClick={(e) => setPage(e.key)} style={{ borderInlineEnd: 0 }}
            items={pages.map((p) => ({ key: p.key, icon: p.icon, label: p.label }))} />
        </Sider>
        <Layout>
          <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', alignItems: 'center', borderBottom: '1px solid #eef0f3' }}>
            <Typography.Title level={4} style={{ margin: 0, flex: 1 }}>{current.label}</Typography.Title>
            <Dropdown menu={{ items: [
              { key: 'pw', label: 'Đổi mật khẩu', onClick: () => setPwOpen(true) },
              { key: 'out', label: 'Đăng xuất', icon: <LogoutOutlined />, onClick: logout },
            ] }}>
              <Button type="text" icon={<UserOutlined />}>{user.username} <Tag style={{ marginLeft: 6 }}>{ROLE_LABEL[user.role]}</Tag></Button>
            </Dropdown>
          </Header>
          <Content style={{ padding: 24, background: '#f5f6f8' }}>{content[current.key]}</Content>
        </Layout>
      </Layout>
      <ChangePassword open={pwOpen} onClose={() => setPwOpen(false)} />
    </ConfigProvider>
  )
}

function ChangePassword({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [form] = Form.useForm()
  const submit = async () => {
    const v = await form.validateFields()
    try {
      await api.changePassword(v.old_password, v.new_password)
      message.success('Đã đổi mật khẩu')
      form.resetFields()
      onClose()
    } catch (e) { message.error((e as Error).message) }
  }
  return (
    <Modal title="Đổi mật khẩu" open={open} onOk={submit} onCancel={onClose} okText="Lưu" cancelText="Hủy" destroyOnHidden>
      <Form form={form} layout="vertical">
        <Form.Item name="old_password" label="Mật khẩu hiện tại" rules={[{ required: true }]}><Input.Password /></Form.Item>
        <Form.Item name="new_password" label="Mật khẩu mới (≥ 10 ký tự, có chữ và số)" rules={[{ required: true, min: 10 }]}><Input.Password /></Form.Item>
      </Form>
    </Modal>
  )
}
