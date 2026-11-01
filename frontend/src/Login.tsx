import { useState } from 'react'
import { Alert, Button, Card, Form, Input, Typography } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { api, auth, type CurrentUser } from './api'

export default function Login({ onLogin }: { onLogin: (u: CurrentUser) => void }) {
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const submit = async (v: { username: string; password: string }) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.login(v.username.trim(), v.password)
      auth.set(res.token)
      onLogin(res.user)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f6f8', padding: 16 }}>
      <Card style={{ width: 380 }}>
        <Typography.Title level={4} style={{ marginTop: 0 }}>Hệ thống phân tích cảm xúc & xu hướng</Typography.Title>
        <Typography.Paragraph type="secondary">Đăng nhập để tiếp tục</Typography.Paragraph>
        {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />}
        <Form layout="vertical" onFinish={submit} requiredMark={false}>
          <Form.Item name="username" label="Tên đăng nhập" rules={[{ required: true, message: 'Nhập tên đăng nhập' }]}>
            <Input prefix={<UserOutlined />} autoFocus autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" label="Mật khẩu" rules={[{ required: true, message: 'Nhập mật khẩu' }]}>
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>Đăng nhập</Button>
        </Form>
      </Card>
    </div>
  )
}
