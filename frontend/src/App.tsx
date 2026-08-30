import { useEffect, useState } from 'react'
import {
  Alert,
  Card,
  Col,
  ConfigProvider,
  Layout,
  Row,
  Spin,
  Statistic,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { api, type StatsResponse } from './api'
import PostsTable from './PostsTable'
import CollectorConfig from './CollectorConfig'

const { Header, Content } = Layout
const { Title, Text } = Typography

type ApiState = 'checking' | 'ok' | 'down'

function App() {
  const [apiState, setApiState] = useState<ApiState>('checking')
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .health()
      .then(() => setApiState('ok'))
      .catch(() => setApiState('down'))

    api
      .stats()
      .then(setStats)
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <ConfigProvider theme={{ token: { colorPrimary: '#1677ff' } }}>
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Title level={4} style={{ color: '#fff', margin: 0 }}>
            Hệ thống phân tích cảm xúc & xu hướng mạng xã hội
          </Title>
          <Tag
            icon={apiState === 'ok' ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            color={apiState === 'ok' ? 'success' : apiState === 'down' ? 'error' : 'default'}
          >
            {apiState === 'checking' && 'Đang kiểm tra API...'}
            {apiState === 'ok' && 'API kết nối OK'}
            {apiState === 'down' && 'Không kết nối được API'}
          </Tag>
        </Header>
        <Content style={{ padding: 24 }}>
          <Tabs
            items={[
              {
                key: 'overview',
                label: 'Tổng quan',
                children: (
                  <>
                    {error && (
                      <Alert
                        style={{ marginBottom: 16 }}
                        type="warning"
                        showIcon
                        message="Không lấy được số liệu thống kê"
                        description={error}
                      />
                    )}
                    {!stats && !error ? (
                      <Spin />
                    ) : (
                      <Row gutter={16}>
                        <Col span={8}>
                          <Card>
                            <Statistic title="Tổng bài thu thập" value={stats?.total_posts ?? 0} />
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card>
                            <Statistic title="Đã phân tích" value={stats?.analyzed ?? 0} />
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card>
                            <Statistic title="Chủ đề nổi" value={0} />
                          </Card>
                        </Col>
                      </Row>
                    )}
                    <Text type="secondary" style={{ display: 'block', marginTop: 24 }}>
                      "Đã phân tích" và "Chủ đề nổi" sẽ có dữ liệu thật khi mô hình cảm xúc/xu hướng
                      được viết (Giai đoạn 1, 4) — hiện tại thu thập dữ liệu thô (Giai đoạn 2) đã chạy.
                    </Text>
                  </>
                ),
              },
              {
                key: 'posts',
                label: 'Dữ liệu thu thập',
                children: <PostsTable />,
              },
              {
                key: 'collector-config',
                label: 'Cấu hình thu thập',
                children: <CollectorConfig />,
              },
            ]}
          />
        </Content>
      </Layout>
    </ConfigProvider>
  )
}

export default App
