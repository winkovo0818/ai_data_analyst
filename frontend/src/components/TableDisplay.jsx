import React from 'react';
import { Table, Typography, Space } from 'antd';
import { TableOutlined } from '@ant-design/icons';

const { Text } = Typography;

const TableDisplay = ({ table }) => {
  if (!table || !table.columns || !table.rows) {
    return null;
  }

  const formatValue = (value, col) => {
    if (value === null || value === undefined) {
      return '-';
    }

    // 处理日期时间格式 (例如: 2025-09-28T00:00:00)
    if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value)) {
      try {
        const date = new Date(value);
        if (!isNaN(date.getTime())) {
          // 如果是午夜零点，只显示日期部分
          if (value.includes('T00:00:00')) {
            return value.split('T')[0];
          }
          // 否则显示日期和时间
          return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
          }).replace(/\//g, '-');
        }
      } catch (e) {
        // 忽略解析失败，返回原始值
      }
    }

    if (typeof value !== 'number' || Number.isNaN(value)) {
      return value;
    }

    const name = String(col || '');
    const isRatio = /占比|比例|比|率|%/.test(name);
    const isAverage = /平均|均值/.test(name);

    if (isAverage && !isRatio) {
      return Math.round(value).toLocaleString();
    }
    if (isRatio) {
      return (value * 100).toFixed(2) + '%';
    }
    return value.toLocaleString();
  };

  // 转换为 Ant Design Table 格式
  const columns = table.columns.map((col) => ({
    title: col,
    dataIndex: col,
    key: col,
    ellipsis: true,
    render: (text) => <Text style={{ fontSize: 13 }}>{text}</Text>
  }));

  const dataSource = table.rows.map((row, index) => {
    const rowData = { key: index };
    table.columns.forEach((col, colIndex) => {
      rowData[col] = formatValue(row[colIndex], col);
    });
    return rowData;
  });

  return (
    <div className="table-display-container">
      <div className="table-header">
        <Space>
          <TableOutlined style={{ color: '#4f46e5' }} />
          <span style={{ fontSize: 14, fontWeight: 600, color: '#334155' }}>数据预览</span>
        </Space>
        <Text type="secondary" style={{ fontSize: 12 }}>共 {table.rows.length} 行</Text>
      </div>
      <div className="table-content">
        <Table
          columns={columns}
          dataSource={dataSource}
          pagination={table.rows.length > 10 ? {
            pageSize: 10,
            showSizeChanger: true,
            size: 'small',
          } : false}
          scroll={{ x: 'max-content' }}
          size="small"
          bordered={false}
          className="custom-table"
        />
      </div>
    </div>
  );
};

export default TableDisplay;
