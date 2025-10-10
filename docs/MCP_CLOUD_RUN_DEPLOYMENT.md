# MCP Server Cloud Run 部署成功 ✅

**部署时间**: 2025年10月7日

## 📋 部署信息

| 项目 | 值 |
|-----|-----|
| **服务名称** | ministry-data-mcp |
| **项目 ID** | ai-for-god |
| **区域** | us-central1 |
| **服务 URL** | https://ministry-data-mcp-760303847302.us-central1.run.app |
| **版本** | ministry-data-mcp-00002-8jr |
| **镜像** | gcr.io/ai-for-god/ministry-data-mcp:latest |

## 🔐 安全信息

### Bearer Token（请妥善保管！）
```
REDACTED_SECRET
```

**⚠️ 重要提示**: 
- 这个 Token 已保存在 Google Secret Manager 中
- 请将此 Token 保存到密码管理器
- 所有 API 调用都需要此 Token 进行认证

## 🔗 可用端点

| 端点 | URL | 说明 |
|------|-----|------|
| **健康检查** | `/health` | 服务健康状态 |
| **MCP Capabilities** | `/mcp/capabilities` | MCP 服务器能力 |
| **工具列表** | `/mcp/tools` | 列出所有可用工具 |
| **资源列表** | `/mcp/resources` | 列出所有可用资源 |
| **提示词列表** | `/mcp/prompts` | 列出所有提示词 |
| **JSON-RPC** | `/mcp` | MCP JSON-RPC 端点 |
| **SSE Stream** | `/mcp/sse` | Server-Sent Events 流 |

## 🎯 快速测试

### 1. 健康检查
```bash
curl -H "Authorization: Bearer REDACTED_SECRET" \
  https://ministry-data-mcp-760303847302.us-central1.run.app/health
```

### 2. 查看能力
```bash
curl -H "Authorization: Bearer REDACTED_SECRET" \
  https://ministry-data-mcp-760303847302.us-central1.run.app/mcp/capabilities
```

### 3. 列出工具
```bash
curl -H "Authorization: Bearer REDACTED_SECRET" \
  https://ministry-data-mcp-760303847302.us-central1.run.app/mcp/tools
```

### 4. 列出资源
```bash
curl -H "Authorization: Bearer REDACTED_SECRET" \
  https://ministry-data-mcp-760303847302.us-central1.run.app/mcp/resources
```

## 📱 Claude Desktop 配置

### macOS / Linux
编辑 `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ministry-data": {
      "url": "https://ministry-data-mcp-760303847302.us-central1.run.app/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer REDACTED_SECRET"
      }
    }
  }
}
```

### Windows
编辑 `%APPDATA%\Claude\claude_desktop_config.json` 使用相同配置。

### 应用配置
```bash
# 重启 Claude Desktop 以应用配置
# macOS
killall Claude && open -a Claude

# Windows
# 关闭并重新打开 Claude Desktop
```

## 🐍 Python 调用示例

```python
import requests

# 配置
BASE_URL = "https://ministry-data-mcp-760303847302.us-central1.run.app"
BEARER_TOKEN = "REDACTED_SECRET"
headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}

# 1. 健康检查
response = requests.get(f"{BASE_URL}/health", headers=headers)
print("Health:", response.json())

# 2. 获取工具列表
response = requests.get(f"{BASE_URL}/mcp/tools", headers=headers)
tools = response.json()
print(f"可用工具: {len(tools['tools'])}个")

# 3. 获取资源列表
response = requests.get(f"{BASE_URL}/mcp/resources", headers=headers)
resources = response.json()
print(f"可用资源: {len(resources['resources'])}个")

# 4. 调用工具（JSON-RPC）
response = requests.post(
    f"{BASE_URL}/mcp",
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
)
print("Tools via JSON-RPC:", response.json())

# 5. 读取资源
response = requests.post(
    f"{BASE_URL}/mcp",
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "resources/read",
        "params": {"uri": "ministry://sermon/records"}
    }
)
print("Sermon records:", response.json())

# 6. 调用工具（REST API）
response = requests.post(
    f"{BASE_URL}/mcp/tools/validate_raw_data",
    headers=headers,
    json={"check_duplicates": True, "generate_report": True}
)
print("Validation result:", response.json())
```

## 🔧 管理命令

### 查看服务状态
```bash
gcloud run services describe ministry-data-mcp \
  --region us-central1 \
  --project ai-for-god
```

### 查看日志
```bash
gcloud run logs read ministry-data-mcp \
  --region us-central1 \
  --project ai-for-god \
  --limit 50
```

### 实时日志
```bash
gcloud run logs tail ministry-data-mcp \
  --region us-central1 \
  --project ai-for-god
```

### 更新配置
```bash
# 增加内存
gcloud run services update ministry-data-mcp \
  --memory 1Gi \
  --region us-central1 \
  --project ai-for-god

# 增加 CPU
gcloud run services update ministry-data-mcp \
  --cpu 2 \
  --region us-central1 \
  --project ai-for-god

# 更新环境变量
gcloud run services update ministry-data-mcp \
  --update-env-vars KEY=VALUE \
  --region us-central1 \
  --project ai-for-god
```

### 重新部署（使用新镜像）
```bash
# 1. 构建新镜像
gcloud builds submit \
  --tag gcr.io/ai-for-god/ministry-data-mcp:latest

# 2. 更新服务
gcloud run deploy ministry-data-mcp \
  --image gcr.io/ai-for-god/ministry-data-mcp:latest \
  --region us-central1 \
  --project ai-for-god
```

## 📊 配置详情

| 配置项 | 值 |
|-------|-----|
| **内存** | 512 Mi |
| **CPU** | 1 |
| **超时时间** | 300 秒 |
| **最大实例数** | 10 |
| **最小实例数** | 0 (按需启动) |
| **鉴权** | 启用 (Bearer Token) |
| **公开访问** | 允许 (但需要 Token) |

## 🔐 Secrets 配置

已配置的 Secrets:
1. **mcp-bearer-token**: MCP API 认证 Token
2. **ministry-service-account**: Google Cloud 服务账号密钥

## 📈 监控

### Cloud Console
访问: https://console.cloud.google.com/run/detail/us-central1/ministry-data-mcp

可以查看:
- 请求数量和延迟
- 错误率
- CPU 和内存使用
- 日志和追踪

## 🎉 成功测试

✅ 健康检查通过
```json
{
  "status": "healthy",
  "timestamp": "2025-10-07T22:22:07.218233",
  "auth_required": true
}
```

✅ MCP Capabilities 正常
```json
{
  "protocolVersion": "2024-11-05",
  "capabilities": {
    "tools": {"listChanged": true},
    "resources": {"subscribe": false, "listChanged": true},
    "prompts": {"listChanged": true}
  },
  "serverInfo": {
    "name": "ministry-data",
    "version": "2.0.0",
    "description": "Church Ministry Data Management MCP Server"
  }
}
```

## 📚 相关文档

- [MCP 部署指南](docs/MCP_DEPLOYMENT.md)
- [MCP 快速开始](QUICKSTART_MCP.md)
- [MCP 设计文档](docs/MCP_DESIGN.md)
- [API 文档](docs/API_ENDPOINTS.md)

## 🆘 故障排除

### 如果遇到 401/403 错误
```bash
# 检查 Bearer Token 是否正确
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://ministry-data-mcp-760303847302.us-central1.run.app/health
```

### 如果服务无响应
```bash
# 查看日志
gcloud run logs read ministry-data-mcp --region us-central1 --limit 100
```

### 如果需要更新 Token
```bash
# 更新 Secret
echo -n "NEW_TOKEN" | gcloud secrets versions add mcp-bearer-token --data-file=-

# 重启服务（触发新版本）
gcloud run services update ministry-data-mcp \
  --region us-central1 \
  --update-env-vars DUMMY=restart
```

## ✅ 下一步

1. **配置 Claude Desktop**: 使用上面的配置连接到远程 MCP 服务器
2. **测试工具**: 在 Claude 中测试各种 MCP 工具
3. **监控使用**: 查看 Cloud Run 控制台了解使用情况
4. **设置告警**: 在 Cloud Monitoring 中设置告警通知
5. **定期备份**: 定期备份服务层数据和配置

---

**部署者**: AI Assistant  
**部署日期**: 2025-10-07  
**状态**: ✅ 成功运行

