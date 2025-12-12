# MCP 服务器 - 统一传输实现

这是一个统一的 MCP (Model Context Protocol) 服务器，在单个文件中同时支持 **stdio** 和 **HTTP/SSE** 两种传输模式。

## ✨ 主要特性

- ✅ **双传输模式**：根据环境自动切换 stdio 和 HTTP 模式
- ✅ **Claude Desktop 集成**：通过 stdio 与 Claude Desktop 本地集成
- ✅ **OpenAI/ChatGPT 兼容**：支持 HTTP/SSE 用于 OpenAI Apps SDK
- ✅ **Cloud Run 就绪**：自动检测 Cloud Run 环境
- ✅ **Bearer Token 认证**：HTTP 模式可选认证
- ✅ **单一真实源**：所有 MCP 逻辑在一个文件中 (`mcp_server.py`)

## 📦 工具和资源

### 10个工具（Tools）
1. `query_volunteers_by_date` - 查询指定日期的同工服侍
2. `query_sermon_by_date` - 查询指定日期的证道信息
3. `query_date_range` - 查询时间范围内的数据
4. `clean_ministry_data` - 触发数据清洗管线
5. `generate_service_layer` - 生成服务层数据
6. `validate_raw_data` - 校验原始数据质量
7. `sync_from_gcs` - 从云存储同步数据
8. `check_upcoming_completeness` - 检查未来排班完整性
9. `generate_weekly_preview` - 生成周报预览
10. `get_volunteer_service_counts` - 生成同工服侍次数统计（支持按岗位筛选）

### 22个资源（Resources）
- sermon相关：记录、按讲员查询、系列
- volunteer相关：安排、个人记录、可用性
- stats相关：综合统计、讲员统计、同工统计
- config相关：别名映射

### 12个提示词（Prompts）
- 讲道分析、同工分析、排班助手等预定义模板

## 📖 使用方法

### 1. 本地测试 - stdio 模式（Claude Desktop）

未设置 `PORT` 环境变量时默认使用此模式：

```bash
# 推荐：从项目根目录运行（指向 `mcp/mcp_server.py`）
python mcp/mcp_server.py

# 或者：进入本目录运行
cd service && python mcp_server.py

# 或显式禁用 PORT
unset PORT && python mcp/mcp_server.py
```

**Claude Desktop 配置：**

编辑 `~/.config/Claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "ministry-data": {
      "command": "python",
      "args": ["/path/to/Grace-Irvine-Ministry-Clean/mcp/mcp_server.py"]
    }
  }
}
```

### 2. 本地测试 - HTTP 模式

设置 `PORT` 环境变量或使用 `--http` 标志：

```bash
# HTTP 模式运行在 8080 端口
PORT=8080 python mcp/mcp_server.py

# 或使用 --http 标志
python mcp/mcp_server.py --http
```

**使用 curl 测试：**

```bash
# 健康检查
curl http://localhost:8080/health

# 列出工具
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'

# 获取能力
curl http://localhost:8080/mcp/capabilities
```

### 3. ngrok 测试（用于 OpenAI ChatGPT）

根据 [OpenAI 部署文档](https://developers.openai.com/apps-sdk/deploy)：

```bash
# 启动 HTTP 模式服务器
PORT=8080 python mcp_server.py &

# 通过 ngrok 暴露
ngrok http 8080

# 使用 ngrok HTTPS URL 连接到 ChatGPT
# 示例：https://abc123.ngrok.app/mcp
```

### 4. Cloud Run 部署

Cloud Run 自动设置 `PORT` 环境变量，触发 HTTP 模式：

```bash
# 部署到 Cloud Run
export GCP_PROJECT_ID=your-project-id
export MCP_BEARER_TOKEN=$(openssl rand -hex 32)

./deploy/deploy-mcp.sh
```

部署后的服务将：
- 自动运行在 HTTP/SSE 模式（PORT 由 Cloud Run 设置）
- 支持 OpenAI ChatGPT 连接
- 支持 Claude API 连接
- 需要 Bearer Token 认证

## 🔧 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PORT` | 如果设置，在此端口运行 HTTP 模式 | - (stdio 模式) |
| `MCP_BEARER_TOKEN` | HTTP 认证的 Bearer token | "" (无认证) |
| `MCP_REQUIRE_AUTH` | HTTP 模式是否需要认证 | "true" |
| `CONFIG_PATH` | config.json 文件路径 | `config/config.json` |

## 📡 传输模式检测

服务器自动检测运行模式：

1. **HTTP 模式** - 满足以下任一条件：
   - 设置了 `PORT` 环境变量（Cloud Run 自动设置）
   - 传递了 `--http` 命令行标志

2. **stdio 模式** - 否则（本地 Claude Desktop 默认）

## Architecture

```
mcp_server.py (unified)
├── stdio transport (Claude Desktop)
│   └── MCP SDK stdio protocol
├── HTTP/SSE transport (Cloud Run/OpenAI/Claude API)
│   ├── FastAPI application
│   ├── Bearer token authentication
│   ├── CORS middleware
│   └── JSON-RPC 2.0 endpoints
└── Shared MCP handlers
    ├── Tools (9 tools)
    ├── Resources (22 resources)
    └── Prompts (12 prompts)
```

## Endpoints (HTTP Mode)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/mcp/capabilities` | GET | MCP server capabilities |
| `/mcp` | POST | Main MCP JSON-RPC 2.0 endpoint |
| `/mcp/tools` | GET | List all tools (convenience) |
| `/mcp/resources` | GET | List all resources (convenience) |
| `/mcp/prompts` | GET | List all prompts (convenience) |

## Files

- **`mcp_server.py`** - Unified MCP server (stdio + HTTP/SSE)
- **`Dockerfile`** - Docker image for Cloud Run deployment
- **`README.md`** - This file

## Migration Notes

This unified implementation replaces the previous two-file setup:
- ~~`mcp_server.py`~~ (old stdio-only version)
- ~~`mcp_http_server.py`~~ (old HTTP-only version)

All functionality is now in a single `mcp_server.py` file that supports both transports.

## 🔍 故障排除

### 服务器启动模式错误

检查 `PORT` 环境变量是否设置：
```bash
echo $PORT
```

强制 stdio 模式：
```bash
unset PORT
python mcp_server.py
```

强制 HTTP 模式：
```bash
PORT=8080 python mcp_server.py
# 或
python mcp_server.py --http
```

### 认证错误（HTTP 模式）

如果遇到 401/403 错误，检查：
1. `MCP_BEARER_TOKEN` 已在环境变量或 Cloud Run secrets 中设置
2. Bearer token 包含在请求头中：`Authorization: Bearer YOUR_TOKEN`
3. `MCP_REQUIRE_AUTH` 设置正确（默认："true"）

### OpenAI ChatGPT 连接问题

确保：
1. 端点使用 HTTPS（本地测试使用 ngrok）
2. `/mcp` 端点可访问
3. Bearer token 在 ChatGPT 设置中配置
4. 服务器日志显示收到请求

## Links

- [OpenAI Apps SDK Deployment Guide](https://developers.openai.com/apps-sdk/deploy)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Configuration](https://modelcontextprotocol.io/docs/tools/claude-desktop)
