# MCP Server 部署指南

本文档介绍如何将教会主日事工管理系统部署为标准 MCP (Model Context Protocol) 服务器。

## 📋 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [本地开发](#本地开发)
- [Cloud Run 部署](#cloud-run-部署)
- [客户端配置](#客户端配置)
- [鉴权与安全](#鉴权与安全)
- [监控与调试](#监控与调试)
- [常见问题](#常见问题)

---

## 概述

本项目实现了完整的 MCP 服务器，提供两种传输模式：

| 传输模式 | 用途 | 适用场景 |
|---------|------|---------|
| **stdio** | 本地进程通信 | Claude Desktop 本地集成 |
| **HTTP/SSE** | 远程网络访问 | Cloud Run 部署，多客户端访问 |

### MCP 能力

- **Tools (5个)**: 数据清洗、服务层生成、数据校验、别名管理、状态查询
- **Resources (10个)**: 证道记录、同工安排、统计分析、配置管理
- **Prompts (5个)**: 讲道分析、同工均衡、排班助手、质量检查、别名建议

---

## 架构设计

```
┌─────────────────────────────────────────┐
│         AI 客户端                        │
│  (Claude Desktop / Custom Client)       │
└──────────────┬──────────────────────────┘
               │
        MCP 协议（JSON-RPC 2.0）
               │
   ┌───────────┴───────────┐
   │                       │
stdio 模式          HTTP/SSE 模式
   │                       │
   ▼                       ▼
┌──────────┐      ┌──────────────────┐
│ mcp_     │      │ mcp_http_        │
│ server.py│      │ server.py        │
└────┬─────┘      └────┬─────────────┘
     │                 │
     └────────┬────────┘
              ▼
     ┌────────────────────┐
     │  MCP Core Logic    │
     │  - Tools           │
     │  - Resources       │
     │  - Prompts         │
     └────────┬───────────┘
              ▼
     ┌────────────────────┐
     │  Application Layer │
     │  - CleaningPipeline│
     │  - ServiceLayer    │
     │  - Validators      │
     └────────────────────┘
```

---

## 本地开发

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

确保安装了 MCP SDK：
```bash
pip install mcp>=1.0.0 sse-starlette>=2.0.0
```

### 2. stdio 模式测试

```bash
# 启动 MCP Server（stdio 模式）
python3 mcp_server.py

# 或使用测试脚本
./test_mcp_server.sh
# 选择 1 (stdio mode)
```

### 3. HTTP 模式测试

```bash
# 启动 HTTP Server
export MCP_BEARER_TOKEN="test-token-12345"
export MCP_REQUIRE_AUTH="false"
python3 mcp_http_server.py

# 或使用测试脚本
./test_mcp_server.sh
# 选择 2 (HTTP mode)
```

### 4. 测试端点

```bash
# 健康检查
curl http://localhost:8080/health

# 获取能力
curl http://localhost:8080/mcp/capabilities

# 列出工具
curl http://localhost:8080/mcp/tools

# 列出资源
curl http://localhost:8080/mcp/resources

# 列出提示词
curl http://localhost:8080/mcp/prompts

# 调用工具（JSON-RPC）
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'

# 读取资源
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "resources/read",
    "params": {"uri": "ministry://sermon/records"}
  }'
```

---

## Cloud Run 部署

### 1. 准备工作

```bash
# 设置 GCP 项目
export GCP_PROJECT_ID="your-project-id"

# 生成安全的 Bearer Token
export MCP_BEARER_TOKEN=$(openssl rand -hex 32)
echo "Save this token: $MCP_BEARER_TOKEN"

# 可选：设置其他参数
export GCP_REGION="us-central1"
export MCP_SERVICE_NAME="ministry-data-mcp"
export MEMORY="512Mi"
export CPU="1"
```

### 2. 上传 Service Account 到 Secret Manager

```bash
# 创建 secret
gcloud secrets create ministry-service-account \
  --data-file=config/service-account.json \
  --project=$GCP_PROJECT_ID

# 授权访问
gcloud secrets add-iam-policy-binding ministry-service-account \
  --member="serviceAccount:${GCP_PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$GCP_PROJECT_ID
```

### 3. 执行部署

```bash
# 给脚本执行权限
chmod +x deploy-mcp-cloud-run.sh

# 运行部署脚本
./deploy-mcp-cloud-run.sh
```

部署脚本会自动：
1. ✅ 检查 GCP 环境
2. ✅ 启用必要的 API
3. ✅ 构建 Docker 镜像
4. ✅ 部署到 Cloud Run
5. ✅ 配置 Bearer Token Secret
6. ✅ 生成客户端配置

### 4. 手动部署（可选）

```bash
# 构建镜像
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/ministry-data-mcp

# 部署服务
gcloud run deploy ministry-data-mcp \
  --image gcr.io/$GCP_PROJECT_ID/ministry-data-mcp \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --set-env-vars MCP_MODE=http,MCP_REQUIRE_AUTH=true \
  --set-secrets MCP_BEARER_TOKEN=mcp-bearer-token:latest \
  --update-secrets /app/config/service-account.json=ministry-service-account:latest \
  --allow-unauthenticated
```

### 5. 验证部署

```bash
# 获取服务 URL
SERVICE_URL=$(gcloud run services describe ministry-data-mcp \
  --region us-central1 \
  --format 'value(status.url)')

# 测试健康检查
curl -H "Authorization: Bearer $MCP_BEARER_TOKEN" \
  "${SERVICE_URL}/health"

# 测试 MCP 能力
curl -H "Authorization: Bearer $MCP_BEARER_TOKEN" \
  "${SERVICE_URL}/mcp/capabilities"
```

---

## 客户端配置

### Claude Desktop (macOS/Linux)

编辑 `~/.config/Claude/claude_desktop_config.json`:

#### 本地 stdio 模式
```json
{
  "mcpServers": {
    "ministry-data": {
      "command": "python",
      "args": [
        "/absolute/path/to/Grace-Irvine-Ministry-Clean/mcp_server.py"
      ],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json",
        "CONFIG_PATH": "/path/to/config.json"
      }
    }
  }
}
```

#### 远程 HTTP/SSE 模式
```json
{
  "mcpServers": {
    "ministry-data": {
      "url": "https://your-service.run.app/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer YOUR_BEARER_TOKEN_HERE"
      }
    }
  }
}
```

### Claude Desktop (Windows)

配置文件位置: `%APPDATA%\Claude\claude_desktop_config.json`

### 自定义客户端

使用 MCP SDK 连接：

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# stdio 模式
server_params = StdioServerParameters(
    command="python",
    args=["mcp_server.py"],
    env={"CONFIG_PATH": "config/config.json"}
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # 列出工具
        tools = await session.list_tools()
        
        # 调用工具
        result = await session.call_tool(
            "clean_ministry_data",
            {"dry_run": True}
        )
```

---

## 鉴权与安全

### Bearer Token 认证

#### 生成安全 Token

```bash
# 使用 openssl
openssl rand -hex 32

# 使用 Python
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 配置环境变量

```bash
# 启用鉴权（默认）
export MCP_REQUIRE_AUTH=true

# 设置 Bearer Token
export MCP_BEARER_TOKEN="your-secure-token-here"
```

#### 客户端使用

```bash
# HTTP 请求
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-service.run.app/mcp/tools

# Python requests
import requests

headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "https://your-service.run.app/mcp/tools",
    headers=headers
)
```

### 生产环境安全建议

1. **启用鉴权**
   - 设置 `MCP_REQUIRE_AUTH=true`
   - 使用强随机 Token（>= 32 字节）

2. **使用 Secret Manager**
   - 不要在代码中硬编码 Token
   - 使用 Google Secret Manager 存储敏感信息

3. **限制访问**
   ```bash
   # Cloud Run IAM 策略
   gcloud run services add-iam-policy-binding ministry-data-mcp \
     --member="user:admin@example.com" \
     --role="roles/run.invoker"
   ```

4. **启用日志审计**
   - Cloud Run 自动记录所有请求
   - 查看日志：`gcloud run logs read ministry-data-mcp`

5. **配置 CORS**
   - 生产环境限制 `allow_origins`
   - 修改 `mcp_http_server.py` 中的 CORS 配置

6. **速率限制**
   - 使用 Cloud Armor 或 API Gateway
   - 配置每个 IP 的请求限制

---

## 监控与调试

### 查看日志

```bash
# Cloud Run 日志
gcloud run logs read ministry-data-mcp \
  --region us-central1 \
  --limit 50

# 实时日志
gcloud run logs tail ministry-data-mcp \
  --region us-central1

# 过滤错误
gcloud run logs read ministry-data-mcp \
  --region us-central1 \
  --filter="severity>=ERROR"
```

### 性能监控

在 GCP Console 中查看：
- 请求数量和延迟
- 内存和 CPU 使用率
- 错误率
- 冷启动时间

访问：https://console.cloud.google.com/run/detail/{REGION}/{SERVICE_NAME}/metrics

### 调试技巧

#### 1. 本地调试 HTTP 模式

```bash
# 启动服务
export MCP_REQUIRE_AUTH=false
python3 mcp_http_server.py

# 在另一个终端测试
curl http://localhost:8080/mcp/tools | jq
```

#### 2. 测试 JSON-RPC 调用

```bash
# 使用 jq 格式化
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  | jq

# 调用工具
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "validate_raw_data",
      "arguments": {"check_duplicates": true}
    }
  }' | jq
```

#### 3. 检查 MCP 协议消息

启用详细日志：
```python
# 在 mcp_http_server.py 中
logging.basicConfig(level=logging.DEBUG)
```

---

## 常见问题

### Q1: MCP SDK 版本兼容性

**问题**: `mcp` 包安装失败或版本不兼容

**解决**:
```bash
# 使用最新版本
pip install --upgrade mcp

# 或指定兼容版本
pip install mcp==1.0.0
```

### Q2: stdio 模式在 Claude Desktop 中不工作

**问题**: Claude Desktop 无法连接 MCP Server

**检查清单**:
1. ✅ Python 路径正确
2. ✅ 脚本路径使用绝对路径
3. ✅ 环境变量正确设置
4. ✅ 脚本有执行权限

**调试**:
```bash
# 测试脚本是否能运行
python /path/to/mcp_server.py

# 查看 Claude Desktop 日志（macOS）
tail -f ~/Library/Logs/Claude/mcp-server-ministry-data.log
```

### Q3: Cloud Run 部署后返回 401/403

**问题**: 鉴权失败

**解决**:
```bash
# 检查 Secret 是否正确
gcloud secrets versions access latest \
  --secret=mcp-bearer-token

# 检查 Cloud Run 环境变量
gcloud run services describe ministry-data-mcp \
  --region us-central1 \
  --format=yaml

# 更新 Secret
echo -n "new-token" | gcloud secrets versions add mcp-bearer-token --data-file=-
```

### Q4: SSE 连接超时

**问题**: SSE 流中断或超时

**解决**:
- Cloud Run 超时时间默认 300 秒
- 增加超时：`--timeout=600`
- 对于长时间运行的任务，使用 HTTP POST 而非 SSE

### Q5: 资源未找到错误

**问题**: `ministry://sermon/records` 返回 "Data file not found"

**解决**:
```bash
# 确保服务层数据已生成
curl -X POST http://localhost:8080/mcp/tools/generate_service_layer \
  -H "Content-Type: application/json" \
  -d '{
    "domains": ["sermon", "volunteer"],
    "generate_all_years": true
  }'

# 检查日志目录
ls -la logs/service_layer/
```

### Q6: 内存不足 (OOM)

**问题**: Cloud Run 实例因内存不足重启

**解决**:
```bash
# 增加内存
gcloud run services update ministry-data-mcp \
  --memory 1Gi \
  --region us-central1

# 或优化代码，减少内存使用
```

---

## 环境变量参考

| 变量名 | 默认值 | 说明 |
|-------|--------|------|
| `MCP_MODE` | - | `http` 启动 HTTP Server，否则启动 FastAPI App |
| `MCP_REQUIRE_AUTH` | `true` | 是否需要 Bearer Token 鉴权 |
| `MCP_BEARER_TOKEN` | - | Bearer Token（生产环境必须设置） |
| `PORT` | `8080` | 服务端口 |
| `CONFIG_PATH` | `config/config.json` | 配置文件路径 |
| `GOOGLE_APPLICATION_CREDENTIALS` | - | Google Service Account JSON |

---

## 下一步

- [MCP 设计文档](MCP_DESIGN.md) - 完整的架构设计
- [API 文档](API_ENDPOINTS.md) - REST API 参考
- [快速开始](QUICKSTART.md) - 项目入门指南
- [故障排除](TROUBLESHOOTING.md) - 常见问题解决

---

## 支持

如有问题或建议，请：
1. 查看 [MCP 官方文档](https://modelcontextprotocol.io/)
2. 查看 [GitHub Issues](https://github.com/your-repo/issues)
3. 联系项目维护者

---

**最后更新**: 2025-10-07
**MCP 协议版本**: 2024-11-05
**服务版本**: 2.0.0

