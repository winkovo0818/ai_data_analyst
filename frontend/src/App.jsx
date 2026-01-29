import React, { useState, useEffect } from 'react';
import { Layout, Row, Col, Card, Descriptions, Tag, Space, Button, Badge } from 'antd';
import {
  DatabaseOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  BarChartOutlined,
  SettingOutlined,
  RobotOutlined
} from '@ant-design/icons';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import LLMSettings from './components/LLMSettings';
import './App.css';

const { Header, Content } = Layout;

function App() {
  const [dataset, setDataset] = useState(null);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [llmConfig, setLlmConfig] = useState(null);

  // 加载 LLM 配置
  useEffect(() => {
    const savedConfig = localStorage.getItem('llm_config');
    if (savedConfig) {
      try {
        setLlmConfig(JSON.parse(savedConfig));
      } catch (e) {
        console.error('加载 LLM 配置失败:', e);
      }
    }
  }, []);

  const handleSaveSettings = (config) => {
    setLlmConfig(config);
  };

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="logo-container">
          <div className="app-title">
            <BarChartOutlined style={{ fontSize: 24, marginRight: 8 }} />
            <span>AI Data Analyst</span>
          </div>
          <div className="app-subtitle">
            通用结构化数据分析与可视化系统
          </div>
        </div>
        <Space size="middle">
          {llmConfig && (
            <Tag color="success" icon={<RobotOutlined />}>
              {llmConfig.provider === 'openai' ? 'OpenAI' : 'Claude'} - {llmConfig.model}
            </Tag>
          )}
          <Badge dot={!llmConfig} offset={[-5, 5]}>
            <Button
              type="text"
              icon={<SettingOutlined style={{ fontSize: 18 }} />}
              onClick={() => setSettingsVisible(true)}
              style={{ color: '#4b5563' }}
            >
              设置
            </Button>
          </Badge>
        </Space>
      </Header>

      <LLMSettings
        visible={settingsVisible}
        onClose={() => setSettingsVisible(false)}
        onSave={handleSaveSettings}
      />

      <Content className="app-content">
        <Row gutter={[32, 32]}>
          {/* 左侧：文件上传和数据集信息 */}
          <Col xs={24} lg={7} xl={6}>
            <Space direction="vertical" size={24} style={{ width: '100%' }}>
              <FileUpload onDatasetCreated={setDataset} />

              {dataset && (
                <Card
                  title={
                    <Space>
                      <DatabaseOutlined className="card-header-icon" />
                      <span className="card-title">数据集概览</span>
                    </Space>
                  }
                  bordered={false}
                  className="modern-card dataset-info-card"
                  bodyStyle={{ padding: '0 24px 24px' }}
                >
                  <div className="info-item">
                    <span style={{ color: '#6b7280' }}>ID</span>
                    <Tag>{dataset.dataset_id}</Tag>
                  </div>
                  <div className="info-item">
                    <span style={{ color: '#6b7280' }}>总行数</span>
                    <strong>{dataset.row_count.toLocaleString()}</strong>
                  </div>
                  <div className="info-item">
                    <span style={{ color: '#6b7280' }}>总列数</span>
                    <strong>{dataset.column_count}</strong>
                  </div>

                  {dataset.schema && (
                    <div style={{ marginTop: 24 }}>
                      <div style={{
                        marginBottom: 12,
                        fontWeight: 600,
                        fontSize: 14,
                        color: '#374151',
                        display: 'flex',
                        alignItems: 'center'
                      }}>
                        <FileTextOutlined style={{ marginRight: 8, color: '#4f46e5' }} />
                        字段详情
                      </div>
                      <div className="field-list">
                        {dataset.schema.map((col, index) => (
                          <div key={index} className="field-item">
                            <div>
                              <div style={{ fontWeight: 500, color: '#1f2937', fontSize: 13 }}>{col.name}</div>
                              {col.null_ratio > 0 && (
                                <div style={{ fontSize: 10, color: '#ef4444', marginTop: 2 }}>
                                  空值: {(col.null_ratio * 100).toFixed(0)}%
                                </div>
                              )}
                            </div>
                            <Tag color="geekblue" style={{ marginRight: 0, fontSize: 10 }}>{col.type}</Tag>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </Card>
              )}

              {/* 使用提示 */}
              <Card
                title={
                  <Space>
                    <ThunderboltOutlined className="card-header-icon" />
                    <span className="card-title">快速指南</span>
                  </Space>
                }
                size="small"
                bordered={false}
                className="modern-card"
              >
                <ul style={{
                  paddingLeft: 20,
                  margin: 0,
                  color: '#4b5563',
                  fontSize: 13,
                  lineHeight: 1.8
                }}>
                  <li>支持 .xlsx, .csv 格式 (Max 50MB)</li>
                  <li>使用自然语言提问进行分析</li>
                  <li>自动生成可视化图表</li>
                </ul>
              </Card>
            </Space>
          </Col>

          {/* 右侧：对话界面 */}
          <Col xs={24} lg={17} xl={18}>
            {!llmConfig ? (
              <div style={{
                height: 'calc(100vh - 140px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Card bordered={false} className="modern-card" style={{ maxWidth: 500, textAlign: 'center', padding: 40 }}>
                  <div style={{
                    width: 80,
                    height: 80,
                    background: 'rgba(79, 70, 229, 0.1)',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 24px'
                  }}>
                    <SettingOutlined style={{ fontSize: 32, color: '#4f46e5' }} />
                  </div>
                  <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 12 }}>欢迎使用 AI Data Analyst</h2>
                  <p style={{ color: '#6b7280', marginBottom: 32 }}>
                    请先配置大语言模型 (LLM) API Key 以开始智能数据分析之旅。
                  </p>
                  <Button
                    type="primary"
                    size="large"
                    onClick={() => setSettingsVisible(true)}
                    style={{ borderRadius: 12, paddingLeft: 32, paddingRight: 32 }}
                  >
                    配置模型
                  </Button>
                </Card>
              </div>
            ) : (
              <ChatInterface dataset={dataset} llmConfig={llmConfig} />
            )}
          </Col>
        </Row>
      </Content>
    </Layout>
  );
}

export default App;
