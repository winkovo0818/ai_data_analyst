import React from 'react';
import { Table } from 'antd';

const TableDisplay = ({ table }) => {
  if (!table || !table.columns || !table.rows) {
    return null;
  }

  // 转换为 Ant Design Table 格式
  const columns = table.columns.map((col) => ({
    title: col,
    dataIndex: col,
    key: col,
    ellipsis: true,
  }));

  const dataSource = table.rows.map((row, index) => {
    const rowData = { key: index };
    table.columns.forEach((col, colIndex) => {
      rowData[col] = row[colIndex];
    });
    return rowData;
  });

  return (
    <Table
      columns={columns}
      dataSource={dataSource}
      pagination={{
        pageSize: 10,
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 条`,
      }}
      scroll={{ x: 'max-content' }}
      size="small"
      bordered
      style={{ marginTop: 8 }}
    />
  );
};

export default TableDisplay;
