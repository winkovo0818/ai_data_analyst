import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Space, Card, Tag, Collapse, message } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined, BulbOutlined, BarChartOutlined, TableOutlined, AuditOutlined } from '@ant-design/icons';
import { dataService } from '../services/api';
import ChartDisplay from './ChartDisplay';
import TableDisplay from './TableDisplay';
import MessageRenderer from './MessageRenderer';

const { TextArea } = Input;

const ChatInterface = ({ dataset, llmConfig }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [streamingStatus, setStreamingStatus] = useState('');
  const chatAreaRef = useRef(null);

  // 优化的滚动函数：直接操作容器的 scrollTop，避免整个页面抖动
  const scrollToBottom = (behavior = 'smooth') => {
    if (chatAreaRef.current) {
      chatAreaRef.current.scrollTo({
        top: chatAreaRef.current.scrollHeight,
        behavior: behavior,
      });
    }
  };

  // 监听消息变化，智能决定滚动方式
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      // 如果是用户发送的消息，使用瞬间滚动 ('auto')，避免输入框高度缩小时的视觉跳动
      // 如果是 AI 消息或 Loading 状态，使用平滑滚动 ('smooth')
      const behavior = lastMessage.role === 'user' ? 'auto' : 'smooth';
      
      // 给一点点延迟，确保 DOM 已经更新（特别是 Input 高度变化导致容器高度变化之后）
      setTimeout(() => {
        scrollToBottom(behavior);
      }, 10);
    }
  }, [messages, loading]);

  const handleSend = async () => {
    if (!inputValue.trim()) {
      return;
    }

    if (!dataset) {
      message.warning('请先上传文件并创建数据集');
      return;
    }

    const userMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);
    setStreamingContent('');
    setStreamingStatus('');

    try {
      // 使用流式 API
      let finalResult = null;
      let accumulatedContent = '';

      await dataService.analyzeStream(
        inputValue,
        dataset.dataset_id,
        llmConfig,
        (event) => {
          switch (event.type) {
            case 'start':
              setStreamingStatus('正在初始化分析...');
              break;
            case 'step_start':
              setStreamingStatus(`执行步骤 ${event.step}/${event.max_steps}...`);
              break;
            case 'tool_call':
              setStreamingStatus(`调用工具: ${event.tool}`);
              break;
            case 'tool_result':
              if (event.success) {
                setStreamingStatus(`${event.tool} 完成 (${event.latency_ms?.toFixed(0)}ms)`);
              } else {
                const codeLabel = event.error_code ? ` [${event.error_code}]` : '';
                setStreamingStatus(`${event.tool} 失败${codeLabel}: ${event.error}`);
              }
              break;
            case 'answer_chunk':
              accumulatedContent += event.content;
              setStreamingContent(accumulatedContent);
              break;
            case 'complete':
              finalResult = event;
              break;
            case 'heartbeat':
              break;
            case 'error':
              {
                const codeLabel = event.error_code ? `(${event.error_code}) ` : '';
                message.error(`${codeLabel}${event.message || event.error || '请求失败'}`);
              }
              break;
          }
        }
      );

      if (finalResult) {
        let assistantContent = finalResult.answer || '';
        if (finalResult.error) {
          assistantContent = finalResult.answer || finalResult.error;
        }
        if (finalResult.error_code) {
          assistantContent = `${assistantContent}\n\n错误码: ${finalResult.error_code}`;
        }

        const assistantMessage = {
          role: 'assistant',
          content: assistantContent,
          tables: finalResult.tables || [],
          charts: finalResult.charts || [],
          error: Boolean(finalResult.error),
          error_code: finalResult.error_code,
          error_detail: finalResult.error_detail,
          audit: finalResult.trace ? {
            trace_id: finalResult.trace.trace_id,
            steps: finalResult.trace.steps,
            total_steps: finalResult.trace.total_steps,
            llm_tokens: finalResult.trace.llm_tokens,
            llm_cost_usd: finalResult.trace.llm_cost_usd,
            duration_ms: finalResult.trace.duration_ms
          } : null,
          timestamp: new Date(),
          isNew: true,
        };

        setMessages(prev => {
          const oldMessages = prev.map(m => ({ ...m, isNew: false }));
          return [...oldMessages, assistantMessage];
        });
      }
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: `分析失败: ${error.message}`,
        error: true,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      setStreamingContent('');
      setStreamingStatus('');
    }
  };

  const suggestedQuestions = [
    '数据集有多少行和多少列？',
    '各字段的类型是什么？',
    '显示前10行数据',
    '统计各类别的数量',
    '绘制趋势图',
    '各账号退货占比（比例）',
    '按账号统计退货数量 Top5',
    '按月统计销售额的同比/环比变化',
  ];

  return (
    <div className="chat-wrapper">
      <div className="chat-messages-area" ref={chatAreaRef}>
        {messages.length === 0 ? (
          <div style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#9ca3af'
          }}>
            <div style={{
              fontSize: 64,
              marginBottom: 24,
              color: '#e5e7eb',
              background: '#fff',
              borderRadius: '50%',
              padding: 32,
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
            }}>
              <RobotOutlined />
            </div>
            <h3 style={{ fontSize: 18, color: '#374151', marginBottom: 8 }}>AI 数据分析助手</h3>
            <p style={{ marginBottom: 32 }}>上传数据后，您可以直接用自然语言提问</p>
            
            <div style={{ maxWidth: 600, width: '100%' }}>
              <div style={{ fontSize: 12, marginBottom: 12, textAlign: 'center', color: '#6b7280' }}>
                <BulbOutlined /> 试着问问：
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                {suggestedQuestions.map((q, i) => (
                  <Tag
                    key={i}
                    style={{
                      cursor: 'pointer',
                      padding: '6px 12px',
                      fontSize: 13,
                      background: 'white',
                      border: '1px solid #e5e7eb',
                      borderRadius: 20
                    }}
                    onClick={() => setInputValue(q)}
                    className="suggestion-tag"
                  >
                    {q}
                  </Tag>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div key={index} className={`message-bubble-wrapper message-${msg.role}`}>
              <div className={`bubble bubble-${msg.role}`}>
                {msg.role === 'assistant' && (
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 8, 
                    marginBottom: 12, 
                    borderBottom: '1px solid #f3f4f6', 
                    paddingBottom: 8 
                  }}>
                    <RobotOutlined style={{ color: '#4f46e5' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#4b5563' }}>AI Assistant</span>
                  </div>
                )}
                
                <MessageRenderer 
                  content={msg.content} 
                  isUser={msg.role === 'user'} 
                  animate={msg.isNew} 
                  onAnimationComplete={() => scrollToBottom('smooth')}
                />

                {/* 显示表格 */}
                {msg.tables && msg.tables.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                     {msg.tables.map((table, i) => (
                      <Card key={i} size="small" title={<Space><TableOutlined /> 数据预览</Space>} style={{ marginTop: 12 }}>
                        <TableDisplay table={table} />
                      </Card>
                    ))}
                  </div>
                )}

                {/* 显示图表 */}
                {msg.charts && msg.charts.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    {msg.charts.map((chart, i) => (
                      <Card key={i} size="small" title={<Space><BarChartOutlined /> 可视化分析</Space>} style={{ marginTop: 12 }}>
                        <ChartDisplay chart={chart} />
                      </Card>
                    ))}
                  </div>
                )}

                {/* 审计信息 */}
                {msg.audit && (
                  <Collapse
                    ghost
                    size="small"
                    style={{ marginTop: 16, background: '#f9fafb', borderRadius: 8 }}
                    expandIconPosition="end"
                    items={[
                      {
                        key: '1',
                        label: <Space style={{ fontSize: 12, color: '#9ca3af' }}><AuditOutlined /> 分析详情</Space>,
                        children: (
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12, color: '#6b7280' }}>
                            <div>步骤: {msg.audit.total_steps}</div>
                            <div>Tokens: {msg.audit.llm_tokens}</div>
                            <div>耗时: {msg.audit.duration_ms.toFixed(0)}ms</div>
                            <div>成本: ${msg.audit.llm_cost_usd.toFixed(5)}</div>
                          </div>
                        )
                      }
                    ]}
                  />
                )}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="message-bubble-wrapper message-assistant">
            <div className="bubble bubble-assistant">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space>
                  <div className="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span style={{ color: '#6b7280', fontSize: 13 }}>
                    {streamingStatus || '正在思考与分析数据...'}
                  </span>
                </Space>
                {streamingContent && (
                  <div style={{ color: '#374151', fontSize: 14, marginTop: 8 }}>
                    {streamingContent}
                  </div>
                )}
              </Space>
            </div>
          </div>
        )}
      </div>

      <div className="chat-input-area">
        <div className="input-wrapper">
          <TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={dataset ? "输入您的问题，例如：分析各产品的销售趋势..." : "请先上传数据文件..."}
            autoSize={{ minRows: 1, maxRows: 4 }}
            bordered={false}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={!dataset || loading}
            style={{ resize: 'none', padding: '8px 4px' }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={loading}
              disabled={!dataset || !inputValue.trim()}
              shape="round"
              size="middle"
            >
              发送
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
