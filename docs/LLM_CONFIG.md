# LLM 配置说明

## 功能特性

- ✅ 支持自定义 API Key（无需修改后端 .env）
- ✅ 支持自定义 Base URL（支持代理、私有部署）
- ✅ 支持自定义模型选择
- ✅ 支持 OpenAI 和 Anthropic 两种提供商
- ✅ 配置本地持久化（localStorage）
- ✅ 配置测试功能
- ✅ 实时显示当前使用的模型

## 使用方法

### 1. 打开配置界面

点击页面右上角的 **"LLM 配置"** 按钮。

### 2. 配置 OpenAI

1. **提供商**: 选择 `OpenAI`
2. **API Key**: 输入您的 OpenAI API Key（格式：`sk-...`）
   - 获取地址：https://platform.openai.com/api-keys
3. **Base URL**（可选）:
   - 默认：`https://api.openai.com/v1`
   - 如使用代理或私有部署，填入自定义地址
4. **模型**: 选择模型
   - 推荐：`gpt-4-turbo-preview`（最新 GPT-4 Turbo）
   - 经济：`gpt-3.5-turbo`（速度快、成本低）

### 3. 配置 Anthropic (Claude)

1. **提供商**: 选择 `Anthropic`
2. **API Key**: 输入您的 Anthropic API Key（格式：`sk-ant-...`）
   - 获取地址：https://console.anthropic.com/settings/keys
3. **Base URL**（可选）:
   - 默认：`https://api.anthropic.com`
4. **模型**: 选择模型
   - 推荐：`claude-3-5-sonnet-20241022`（最新 Claude 3.5）
   - 最强：`claude-3-opus-20240229`（Claude 3 Opus）

### 4. 测试配置

点击 **"测试连接"** 按钮，系统会发送一个测试请求验证配置是否正确。

### 5. 保存配置

点击 **"保存配置"** 按钮，配置将保存在浏览器本地存储中。

## 配置示例

### OpenAI 配置示例

```json
{
  "provider": "openai",
  "api_key": "sk-proj-...",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4-turbo-preview"
}
```

### Anthropic 配置示例

```json
{
  "provider": "anthropic",
  "api_key": "sk-ant-...",
  "base_url": "https://api.anthropic.com",
  "model": "claude-3-5-sonnet-20241022"
}
```

### 使用代理示例

```json
{
  "provider": "openai",
  "api_key": "sk-proj-...",
  "base_url": "https://your-proxy.com/v1",
  "model": "gpt-4-turbo-preview"
}
```

## 常见问题

### 1. API Key 安全吗？

✅ **安全**。API Key 仅保存在您的浏览器本地存储（localStorage）中，不会上传到服务器或第三方。

### 2. 配置保存在哪里？

配置保存在浏览器的 localStorage 中，刷新页面后仍然有效。如果清除浏览器数据，配置会丢失。

### 3. 可以使用其他 LLM 吗？

目前支持 OpenAI 和 Anthropic。如果您的 LLM 兼容 OpenAI API，可以选择 `OpenAI` 提供商，并设置自定义 Base URL。

### 4. 测试连接失败怎么办？

检查以下项：
- API Key 是否正确
- Base URL 是否正确（如果填写了）
- 网络连接是否正常
- API Key 是否有足够的配额

### 5. 如何切换模型？

直接在配置界面选择新的模型并保存即可，无需重启服务。

### 6. 成本如何计算？

每次分析请求会在响应中返回 Token 消耗和成本信息，可在"查看执行详情"中查看。

## 推荐配置

### 高性能场景
- **OpenAI**: `gpt-4-turbo-preview`
- **Anthropic**: `claude-3-opus-20240229`

### 平衡性价比
- **OpenAI**: `gpt-4o-mini`
- **Anthropic**: `claude-3-5-sonnet-20241022`（推荐）

### 低成本场景
- **OpenAI**: `gpt-3.5-turbo`
- **Anthropic**: `claude-3-haiku-20240307`

## 注意事项

1. **API Key 有效期**: 定期检查 API Key 是否过期
2. **配额限制**: 注意您的 API 账户配额
3. **网络环境**: 如果在国内使用，可能需要配置代理
4. **模型选择**: 不同模型的能力和成本差异较大，根据需求选择

## 故障排查

### 错误：未配置 API Key

**原因**: 没有配置 LLM 或配置未保存

**解决**: 点击"LLM 配置"按钮，填入 API Key 并保存

### 错误：配置测试失败

**原因**: API Key 无效或网络问题

**解决**:
1. 检查 API Key 是否正确
2. 测试网络连接
3. 检查 Base URL 设置

### 错误：模型不支持

**原因**: 选择的模型名称错误或账户没有权限

**解决**: 选择其他可用模型或联系 API 提供商

---

更多帮助，请参考：
- [OpenAI API 文档](https://platform.openai.com/docs)
- [Anthropic API 文档](https://docs.anthropic.com)
