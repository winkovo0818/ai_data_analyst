import React, { useState } from 'react';
import { Upload, Button, Card, message, Select, InputNumber, Space, Tag, Typography } from 'antd';
import { InboxOutlined, FileExcelOutlined, CheckCircleFilled, CloudUploadOutlined, FileTextOutlined } from '@ant-design/icons';
import { dataService } from '../services/api';

const { Dragger } = Upload;
const { Text } = Typography;

const FileUpload = ({ onDatasetCreated }) => {
  const [fileInfo, setFileInfo] = useState(null);
  const [selectedSheet, setSelectedSheet] = useState(null);
  const [headerRow, setHeaderRow] = useState(1);
  const [uploading, setUploading] = useState(false);
  const [creating, setCreating] = useState(false);

  const uploadProps = {
    name: 'file',
    multiple: false,
    accept: '.xlsx,.xls,.csv',
    showUploadList: false,
    beforeUpload: async (file) => {
      // 检查文件类型
      const isValidType = file.name.endsWith('.xlsx') ||
                         file.name.endsWith('.xls') ||
                         file.name.endsWith('.csv');
      if (!isValidType) {
        message.error('只支持 Excel (.xlsx, .xls) 和 CSV (.csv) 文件');
        return false;
      }

      // 检查文件大小 (50MB)
      const isLt50M = file.size / 1024 / 1024 < 50;
      if (!isLt50M) {
        message.error('文件大小不能超过 50MB');
        return false;
      }

      setUploading(true);
      try {
        const result = await dataService.uploadFile(file);
        setFileInfo(result);
        if (result.sheets && result.sheets.length > 0) {
          setSelectedSheet(result.sheets[0]);
        }
        message.success('文件上传成功');
      } catch (error) {
        message.error(`上传失败: ${error.message}`);
      } finally {
        setUploading(false);
      }

      return false; // 阻止自动上传
    },
  };

  const handleCreateDataset = async () => {
    if (!fileInfo) {
      message.warning('请先上传文件');
      return;
    }

    setCreating(true);
    try {
      const dataset = await dataService.createDataset(
        fileInfo.file_id,
        selectedSheet,
        headerRow
      );
      message.success('数据集创建成功');
      onDatasetCreated(dataset);
      // 重置状态
      setFileInfo(null);
      setSelectedSheet(null);
      setHeaderRow(1);
    } catch (error) {
      message.error(`创建数据集失败: ${error.message}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <Card
      title={
        <Space>
          <CloudUploadOutlined className="card-header-icon" />
          <span className="card-title">导入数据</span>
        </Space>
      }
      className="modern-card"
      bordered={false}
      bodyStyle={{ padding: 24 }}
    >
      {!fileInfo ? (
        <Dragger
          {...uploadProps}
          className="upload-dragger"
          style={{
            background: '#f9fafb',
            border: '2px dashed #e5e7eb',
            borderRadius: 16,
            padding: 20
          }}
        >
          <div className="upload-icon">
            <InboxOutlined />
          </div>
          <p className="ant-upload-text" style={{ fontSize: 15, fontWeight: 500, color: '#374151' }}>
            点击或拖拽文件到此处
          </p>
          <p className="ant-upload-hint" style={{ color: '#9ca3af', fontSize: 12 }}>
            支持 Excel (.xlsx) 或 CSV<br />最大 50MB
          </p>
        </Dragger>
      ) : (
        <div style={{ animation: 'fadeIn 0.3s ease' }}>
          <div style={{
            padding: 16,
            background: '#f0fdf4',
            borderRadius: 12,
            border: '1px solid #dcfce7',
            marginBottom: 20
          }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <CheckCircleFilled style={{ color: '#16a34a', fontSize: 18 }} />
                <Text strong style={{ color: '#166534' }}>{fileInfo.filename}</Text>
              </Space>
              <Tag color="success">{(fileInfo.size_bytes / 1024).toFixed(1)} KB</Tag>
            </Space>
          </div>

          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            {fileInfo.sheets && (
              <div>
                <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>选择工作表 (Sheet)</div>
                <Select
                  value={selectedSheet}
                  onChange={setSelectedSheet}
                  style={{ width: '100%' }}
                  size="large"
                >
                  {fileInfo.sheets.map(sheet => (
                    <Select.Option key={sheet} value={sheet}>
                      {sheet}
                    </Select.Option>
                  ))}
                </Select>
              </div>
            )}

            <div>
              <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>表头行号</div>
              <InputNumber
                min={1}
                max={100}
                value={headerRow}
                onChange={setHeaderRow}
                style={{ width: '100%' }}
                size="large"
              />
            </div>

            <div style={{ marginTop: 8, display: 'flex', gap: 12 }}>
              <Button
                block
                size="large"
                onClick={() => setFileInfo(null)}
              >
                取消
              </Button>
              <Button
                type="primary"
                block
                onClick={handleCreateDataset}
                loading={creating}
                size="large"
                style={{
                  boxShadow: '0 4px 6px -1px rgba(79, 70, 229, 0.2)'
                }}
              >
                开始分析
              </Button>
            </div>
          </Space>
        </div>
      )}
    </Card>
  );
};

export default FileUpload;
