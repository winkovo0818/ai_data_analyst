import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

export const dataService = {
  // 上传文件
  uploadFile: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // 创建数据集
  createDataset: (fileId, sheet = null, headerRow = 1) => {
    const formData = new FormData();
    formData.append('file_id', fileId);
    if (sheet) {
      formData.append('sheet', sheet);
    }
    formData.append('header_row', headerRow);
    return api.post('/dataset/create', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // 获取数据集 Schema
  getSchema: (datasetId) => {
    return api.get(`/dataset/${datasetId}/schema`);
  },

  // 分析数据
  analyze: (question, datasetId, llmConfig = null) => {
    const payload = {
      question,
      dataset_id: datasetId,
    };

    // 如果提供了 LLM 配置，添加到请求中
    if (llmConfig) {
      payload.llm_config = llmConfig;
    }

    return api.post('/analyze', payload);
  },

  // 流式分析数据 (SSE)
  analyzeStream: (question, datasetId, llmConfig, onEvent) => {
    const payload = {
      question,
      dataset_id: datasetId,
    };

    if (llmConfig) {
      payload.llm_config = llmConfig;
    }

    return new Promise((resolve, reject) => {
      fetch('/api/analyze/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          function read() {
            reader.read().then(({ done, value }) => {
              if (done) {
                resolve();
                return;
              }

              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split('\n\n');
              buffer = lines.pop() || '';

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.slice(6));
                    onEvent(data);

                    // 如果是完成事件，resolve
                    if (data.type === 'complete') {
                      resolve(data);
                    }
                  } catch (e) {
                    console.error('解析 SSE 数据失败:', e);
                  }
                }
              }

              read();
            }).catch(reject);
          }

          read();
        })
        .catch(reject);
    });
  },

  // 健康检查
  health: () => {
    return api.get('/health');
  },
};

export default api;
