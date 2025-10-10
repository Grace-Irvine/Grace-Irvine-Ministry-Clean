# MCP Service - AI助手集成服务

Model Context Protocol (MCP) 服务器，提供AI助手（如Claude Desktop、ChatGPT）与教会数据管理系统的集成。

## 🎯 功能

### MCP协议支持
- **Tools**: 5个工具用于执行操作（清洗数据、生成服务层、验证等）
- **Resources**: 10个资源用于数据访问（证道、同工、统计数据）
- **Prompts**: 6个提示词模板用于常见分析任务
- **双传输模式**: stdio（本地）+ HTTP/SSE（远程）

### Tools（工具）
1. `query_volunteers_by_date` - 查询指定日期的同工安排
2. `query_sermon_by_date` - 查询指定日期的证道信息
3. `query_date_range` - 查询日期范围内的服侍安排

### Resources（资源）
- `ministry://sermon/records` - 证道记录
- `ministry://sermon/by-preacher/{name}` - 按讲员查询
- `ministry://volunteer/assignments` - 同工安排
- `ministry://volunteer/by-person/{id}` - 个人服侍记录
- `ministry://stats/preachers` - 讲员统计
- `ministry://stats/volunteers` - 同工统计
- 更多...

### Prompts（提示词）
1. `analyze_preaching_schedule` - 分析讲道安排
2. `analyze_volunteer_balance` - 分析同工服侍均衡性
3. `find_scheduling_gaps` - 查找排班空缺
4. `analyze_next_sunday_volunteers` - 分析下周日同工
5. `analyze_volunteer_frequency` - 分析服侍频率
6. `analyze_recent_volunteer_roles` - 分析最近的岗位分布

## 🚀 本地开发

### stdio模式（Claude Desktop）

#### 安装
```bash
# 编辑Claude Desktop配置
# macOS: ~/.config/Claude/claude_desktop_config.json
# Windows: %APPDATA%\Claude\claude_desktop_config.json

{
  "mcpServers": {
    "ministry-data": {
      "command": "python",
      "args": ["/path/to/mcp/mcp_server.py"]
    }
  }
}
```

#### 测试
```bash
# 从项目根目录
python mcp/mcp_server.py
```

### HTTP/SSE模式（远程访问）

#### 运行
```bash
# 从项目根目录
export MCP_BEARER_TOKEN=$(openssl rand -hex 32)
python mcp/mcp_http_server.py
```

服务将在 http://localhost:8080 启动

#### 测试
```bash
# 获取能力
curl http://localhost:8080/mcp/capabilities

# 列出工具
curl http://localhost:8080/mcp/tools

# 列出资源
curl http://localhost:8080/mcp/resources
```

## 📦 Docker部署

### 构建镜像
```bash
# 从项目根目录
docker build -f mcp/Dockerfile -t ministry-data-mcp .
```

### 运行容器
```bash
docker run -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  -e PORT=8080 \
  -e MCP_BEARER_TOKEN=your-token \
  ministry-data-mcp
```

## ☁️ Cloud Run部署

### 快速部署
```bash
# 设置环境变量
export GCP_PROJECT_ID=your-project-id
export MCP_BEARER_TOKEN=$(openssl rand -hex 32)

# 部署
cd deploy
./deploy-mcp.sh
```

### 环境变量
- `PORT`: 服务端口（默认8080）
- `MCP_BEARER_TOKEN`: Bearer认证令牌
- `MCP_REQUIRE_AUTH`: 是否需要认证（默认true）
- `GOOGLE_APPLICATION_CREDENTIALS`: 服务账号路径

## 🔧 架构

### 目录结构
```
mcp/
├── mcp_server.py        # stdio模式服务器
├── mcp_http_server.py   # HTTP/SSE模式服务器
├── Dockerfile           # Docker构建文件
└── README.md            # 本文档
```

### 依赖
- **mcp SDK**: Model Context Protocol实现
- **FastAPI**: HTTP/SSE服务器框架
- **core/***: 共享业务逻辑

### 数据流
```
AI助手 ←→ MCP Server ←→ core/* ←→ Google Sheets/Cloud Storage
```

## 🤖 AI助手集成

### Claude Desktop
```json
{
  "mcpServers": {
    "ministry-data": {
      "url": "https://ministry-data-mcp-xxx.run.app/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

### 对话示例
```
用户: "请分析2024年的讲道安排"
Claude: [使用analyze_preaching_schedule提示词]
        分析结果...

用户: "10月份还有哪些周日没安排敬拜带领？"
Claude: [使用find_scheduling_gaps工具]
        查询结果...
```

## 📊 监控

### 日志
```bash
# Cloud Run日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-mcp" --limit 50
```

### 健康检查
```bash
curl https://ministry-data-mcp-xxx.run.app/health
```

## 🧪 测试

### 测试MCP工具
```bash
# 使用MCP Inspector
npx @modelcontextprotocol/inspector python mcp/mcp_server.py
```

### 测试HTTP端点
```bash
# 测试工具调用
curl -X POST http://localhost:8080/mcp \
  -H "Authorization: Bearer $MCP_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

## 🔗 相关文档
- [MCP设计文档](../docs/MCP_DESIGN.md)
- [MCP部署指南](../docs/MCP_DEPLOYMENT.md)
- [MCP集成指南](../docs/MCP_INTEGRATION.md)
- [主README](../README.md)

