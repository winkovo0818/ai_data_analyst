import React, { useState, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Modal, Button, Space, Tooltip, Empty } from 'antd';
import { 
  FullscreenOutlined, 
  DownloadOutlined, 
  BarChartOutlined,
  ExpandOutlined,
  CopyOutlined,
  CheckOutlined
} from '@ant-design/icons';

const ChartDisplay = ({ chart }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const chartOption = useMemo(() => {
    if (!chart || !chart.option) return null;

    // 深度克隆并优化配置
    const option = JSON.parse(JSON.stringify(chart.option));

    // 注入更好的默认样式
    const colors = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];
    
    return {
      ...option,
      color: colors,
      backgroundColor: 'transparent',
      textStyle: {
        fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      },
      animationDuration: 1500,
      animationEasing: 'cubicOut',
      tooltip: {
        trigger: 'axis',
        ...option.tooltip,
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: { color: '#1e293b', fontSize: 13 },
        extraCssText: 'box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); border-radius: 8px; border: none;',
        padding: [10, 14],
        axisPointer: {
          lineStyle: { color: '#e2e8f0', width: 2 }
        }
      },
      legend: {
        bottom: 0,
        itemWidth: 12,
        itemHeight: 12,
        textStyle: { color: '#64748b', fontSize: 12 },
        ...option.legend
      },
      grid: {
        containLabel: true,
        left: '2%',
        right: '2%',
        bottom: '12%',
        top: '12%',
        ...option.grid
      },
      xAxis: option.xAxis ? {
        ...option.xAxis,
        axisLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { color: '#94a3b8', fontSize: 11, margin: 12 },
        splitLine: { show: false }
      } : undefined,
      yAxis: option.yAxis ? {
        ...option.yAxis,
        axisLine: { show: false },
        axisLabel: { color: '#94a3b8', fontSize: 11, margin: 12 },
        splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
      } : undefined,
      series: (option.series || []).map(s => ({
        ...s,
        smooth: s.type === 'line' ? true : s.smooth,
        symbolSize: 8,
        itemStyle: {
          borderRadius: s.type === 'bar' ? [4, 4, 0, 0] : undefined,
          ...s.itemStyle
        }
      }))
    };
  }, [chart]);

  if (!chart || !chart.option) {
    return <Empty description="暂无图表数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  const handleDownload = () => {
    const chartInstance = document.querySelector('.echarts-for-react canvas');
    if (chartInstance) {
      const url = chartInstance.toDataURL('image/png');
      const link = document.createElement('a');
      link.download = `${chart.title || 'chart'}.png`;
      link.href = url;
      link.click();
    }
  };

  const handleCopyOption = () => {
    navigator.clipboard.writeText(JSON.stringify(chart.option, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const ChartHeader = () => (
    <div className="chart-header">
      <div className="chart-title">
        <BarChartOutlined className="title-icon" />
        <span>{chart.title || '可视化图表'}</span>
      </div>
      <Space size={8}>
        <Tooltip title="复制代码">
          <Button 
            type="text" 
            size="small" 
            icon={copied ? <CheckOutlined style={{ color: '#52c41a' }} /> : <CopyOutlined />} 
            onClick={handleCopyOption} 
          />
        </Tooltip>
        <Tooltip title="下载图片">
          <Button type="text" size="small" icon={<DownloadOutlined />} onClick={handleDownload} />
        </Tooltip>
        <Tooltip title="全屏查看">
          <Button type="text" size="small" icon={<ExpandOutlined />} onClick={() => setIsModalOpen(true)} />
        </Tooltip>
      </Space>
    </div>
  );

  return (
    <div className="chart-display-container">
      <ChartHeader />
      <div className="chart-content">
        <ReactECharts
          option={chartOption}
          style={{ height: '360px', width: '100%' }}
          notMerge={true}
          lazyUpdate={true}
          theme={"light"}
        />
      </div>

      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChartOutlined style={{ color: '#4f46e5' }} />
            <span>{chart.title || '图表全屏查看'}</span>
          </div>
        }
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        width="90vw"
        centered
        className="chart-fullscreen-modal"
      >
        <div style={{ height: '75vh', minHeight: '500px' }}>
          <ReactECharts
            option={chartOption}
            style={{ height: '100%', width: '100%' }}
            notMerge={true}
            lazyUpdate={true}
            theme={"light"}
          />
        </div>
      </Modal>
    </div>
  );
};

export default ChartDisplay;
