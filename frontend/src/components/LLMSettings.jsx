import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Button, Space, message, Tabs, Typography } from 'antd';
import { SettingOutlined } from '@ant-design/icons';

const { Text, Link } = Typography;

const LLMSettings = ({ visible, onClose, onSave }) => {
  const [form] = Form.useForm();
  const [testing, setTesting] = useState(false);

  // 加载保存的配置
  useEffect(() => {
    if (visible) {
      const savedConfig = localStorage.getItem('llm_config');
      if (savedConfig) {
        try {
          const config = JSON.parse(savedConfig);
          form.setFieldsValue(config);
        } catch (e) {
          console.error('加载配置失败:', e);
        }
      } else {
        // 默认配置
        form.setFieldsValue({
          provider: 'openai',
          model: 'gpt-4-turbo-preview',
        });
      }
    }
  }, [visible, form]);

  const handleSave = () => {
    form.validateFields().then((values) => {
      // 保存到 localStorage
      localStorage.setItem('llm_config', JSON.stringify(values));
      message.success('LLM 配置已保存');
      onSave(values);
      onClose();
    });
  };

  const handleTest = async () => {
    try {
      await form.validateFields();
      setTesting(true);

      const values = form.getFieldsValue();

      // 简单测试：发送一个测试请求
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: '你好，请回复"配置测试成功"',
          llm_config: values,
        }),
      });

      if (response.ok) {
        message.success('配置测试成功！LLM 连接正常');
      } else {
        const error = await response.json();
        let errorMsg = '未知错误';
        if (typeof error.detail === 'string') {
          errorMsg = error.detail;
        } else if (Array.isArray(error.detail)) {
          errorMsg = error.detail.map(e => e.msg || JSON.stringify(e)).join('; ');
        } else if (error.detail) {
          errorMsg = JSON.stringify(error.detail);
        }
        message.error(`配置测试失败: ${errorMsg}`);
      }
    } catch (error) {
      message.error(`配置测试失败: ${error.message}`);
    } finally {
      setTesting(false);
    }
  };

  const handleClear = () => {
    localStorage.removeItem('llm_config');
    form.resetFields();
    form.setFieldsValue({
      provider: 'openai',
      model: 'gpt-4-turbo-preview',
    });
    message.info('已清除保存的配置');
  };

  const provider = Form.useWatch('provider', form);

  const helpContent = (type) => (
    <div style={{ padding: '8px 0', fontSize: 13, color: '#666' }}>
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <div>
          <Text strong>获取 API Key:</Text>
          <ol style={{ paddingLeft: 20, marginTop: 8, lineHeight: 1.6 }}>
            {type === 'openai' ? (
              <li>访问 <Link href="https://platform.openai.com/api-keys" target="_blank">OpenAI API Keys</Link></li>
            ) : (
              <li>访问 <Link href="https://console.anthropic.com/settings/keys" target="_blank">Anthropic Console</Link></li>
            )}
            <li>创建新的 API Key</li>
            <li>复制并粘贴到上方</li>
          </ol>
        </div>
        <div>
          <Text strong>推荐模型:</Text>
          <ul style={{ paddingLeft: 20, marginTop: 8, lineHeight: 1.6 }}>
            {type === 'openai' ? (
              <>
                <li><Text code>gpt-4-turbo-preview</Text> - 最新 GPT-4 Turbo（推荐）</li>
                <li><Text code>gpt-3.5-turbo</Text> - 成本低，速度快</li>
              </>
            ) : (
              <>
                <li><Text code>claude-3-5-sonnet-20241022</Text> - 最新 Claude 3.5（推荐）</li>
                <li><Text code>claude-3-opus-20240229</Text> - 最强性能</li>
              </>
            )}
          </ul>
        </div>
      </Space>
    </div>
  );

  return (
    <Modal
      title={
        <Space>
          <SettingOutlined />
          <span>LLM 配置</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={600}
      footer={[
        <Button key="clear" onClick={handleClear}>
          清除配置
        </Button>,
        <Button key="test" onClick={handleTest} loading={testing}>
          测试连接
        </Button>,
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button key="save" type="primary" onClick={handleSave}>
          保存配置
        </Button>,
      ]}
    >
      <Form
        form={form}
        layout="vertical"
        style={{ marginTop: 20 }}
      >
        <Form.Item
          label="LLM 提供商"
          name="provider"
          rules={[{ required: true, message: '请选择 LLM 提供商' }]}
        >
          <Select>
            <Select.Option value="openai">OpenAI</Select.Option>
            <Select.Option value="anthropic">Anthropic (Claude)</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item
          label="API Key"
          name="api_key"
          rules={[{ required: true, message: '请输入 API Key' }]}
          extra="您的 API Key 仅保存在浏览器本地，不会上传到服务器"
        >
          <Input.Password
            placeholder={
              provider === 'openai'
                ? 'sk-...'
                : 'sk-ant-...'
            }
          />
        </Form.Item>

        <Form.Item
          label="Base URL"
          name="base_url"
          extra="可选，用于自定义 API 端点（如使用代理或私有部署）"
        >
          <Input
            placeholder={
              provider === 'openai'
                ? 'https://api.openai.com/v1'
                : 'https://api.anthropic.com'
            }
          />
        </Form.Item>

        <Form.Item
          label="模型"
          name="model"
          rules={[{ required: true, message: '请输入模型名称' }]}
          extra="直接输入模型名称，如 gpt-4-turbo-preview, claude-3-5-sonnet-20241022 等"
        >
          <Input
            placeholder="输入模型名称，如 gpt-4-turbo-preview"
          />
        </Form.Item>
      </Form>

      <Tabs
        style={{ marginTop: 24 }}
        items={[
          {
            key: 'openai',
            label: 'OpenAI 配置示例',
            children: helpContent('openai'),
          },
          {
            key: 'anthropic',
            label: 'Anthropic 配置示例',
            children: helpContent('anthropic'),
          },
        ]}
      />
    </Modal>
  );
};

export default LLMSettings;
