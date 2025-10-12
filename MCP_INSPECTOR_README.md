# 使用 MCP Inspector 检查已部署的 MCP 服务器

## 快速开始 ⚡

### 最简单的方法（推荐）

```bash
# 1. 运行快速测试（验证服务器正常）
bash test_mcp_quick.sh

# 2. 启动 MCP Inspector（图形界面）
bash inspect_cloud_mcp.sh
```

就这么简单！🎉

## 工具概览

### 📁 项目中新增的文件

| 文件 | 用途 |
|------|------|
| `inspect_cloud_mcp.sh` | 启动 MCP Inspector 连接云端服务器 |
| `test_mcp_quick.sh` | 快速测试所有 MCP 功能 |
| `INSPECTOR_QUICKSTART.md` | 快速入门指南 |
| `docs/MCP_INSPECTOR_GUIDE.md` | 完整使用指南 |
| `config/claude_desktop_config_cloud.json` | Claude Desktop 配置 |

## 使用场景

### 🔍 场景 1: 验证部署

```bash
# 部署后立即测试
bash test_mcp_quick.sh
```

输出示例：
```
✓ Health check passed
✓ Found 9 tools
✓ Found 27 resources
✓ Tool invocation successful
✓ Resource read successful
✓ All tests passed!
```

### 🖥️ 场景 2: 图形界面调试

```bash
# 启动 Inspector
bash inspect_cloud_mcp.sh
```

会在浏览器中打开交互界面，可以：
- 🔧 浏览和测试所有工具
- 📚 查看所有资源
- 📊 实时查看请求/响应
- 🐛 调试问题

### 🧪 场景 3: 命令行测试

```bash
# 设置环境变量
export MCP_URL="https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app"
export TOKEN="Bearer REDACTED_SECRET"

# 测试健康状态
curl -H "Authorization: $TOKEN" "$MCP_URL/health" | jq .

# 列出工具
curl -X POST "$MCP_URL/mcp" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools[].name'
```

## 已部署的服务信息

### 🌐 服务 URL
```
https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app
```

### 🔑 认证
```
Bearer Token: REDACTED_SECRET
```

**⚠️ 重要**: 这个 Token 请妥善保管，不要泄露！

### 📡 端点

| 端点 | 用途 |
|------|------|
| `/health` | 健康检查 |
| `/mcp` | MCP JSON-RPC 接口 |
| `/mcp/sse` | SSE 流式连接（用于 Claude Desktop） |
| `/mcp/tools` | 工具列表 |
| `/mcp/resources` | 资源列表 |
| `/mcp/prompts` | 提示词列表 |

## 可用功能

### 🔧 9 个工具

1. **query_volunteers_by_date** - 查询同工服侍安排
2. **query_sermon_by_date** - 查询证道信息
3. **query_date_range** - 查询日期范围
4. **check_upcoming_completeness** - 检查排班完整性
5. **generate_weekly_preview** - 生成周报预览
6. **analyze_role_coverage** - 分析岗位覆盖率
7. **analyze_preacher_rotation** - 分析讲员轮换
8. **analyze_sermon_series_progress** - 分析证道系列进度
9. **analyze_volunteer_trends** - 分析同工趋势

### 📚 27 个资源

分为 6 大类：
- **基础数据**: sermon-records, volunteer-assignments
- **统计信息**: ministry-stats, preacher-stats, volunteer-stats
- **历史分析**: volunteer-frequency-history, series-progression-history
- **当前状态**: current-week-overview, current-volunteer-status
- **未来规划**: future-upcoming-services, future-scheduling-suggestions
- **配置**: alias-mappings

## 常见操作

### 查询下周主日

```bash
curl -X POST https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp \
  -H "Authorization: Bearer REDACTED_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "generate_weekly_preview",
      "arguments": {"format": "markdown"}
    }
  }' | jq -r '.result.content[0].text'
```

### 检查未来排班

```bash
curl -X POST https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp \
  -H "Authorization: Bearer REDACTED_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "check_upcoming_completeness",
      "arguments": {"weeks_ahead": 4}
    }
  }' | jq .
```

### 读取统计摘要

```bash
curl -X POST https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp \
  -H "Authorization: Bearer REDACTED_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "resources/read",
    "params": {"uri": "ministry://stats/summary"}
  }' | jq -r '.result.contents[0].text' | jq .
```

## MCP Inspector 界面指南

### 启动 Inspector

```bash
bash inspect_cloud_mcp.sh
```

### 界面布局

```
┌─────────────────────────────────────────┐
│  🔧 Tools  📚 Resources  💬 Prompts     │
├─────────────────────────────────────────┤
│                                         │
│  [工具列表]           [工具详情]        │
│  • Tool 1            参数输入框         │
│  • Tool 2            执行按钮           │
│  • Tool 3            结果显示           │
│                                         │
├─────────────────────────────────────────┤
│  📝 Request/Response Logs               │
│  [显示所有请求和响应的日志]             │
└─────────────────────────────────────────┘
```

### 使用步骤

1. **连接服务器**: 自动连接到云端 MCP
2. **浏览工具**: 在 Tools 面板查看所有工具
3. **测试工具**: 点击工具 → 填写参数 → Execute
4. **查看资源**: 切换到 Resources 面板浏览数据
5. **检查日志**: 在 Logs 面板查看请求详情

## 故障排除

### ❌ 无法连接

```bash
# 1. 检查服务器状态
gcloud run services describe ministry-data-mcp --region us-central1

# 2. 查看日志
gcloud run services logs read ministry-data-mcp --region us-central1 --limit 50

# 3. 测试健康端点
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/health
```

### ❌ 认证失败

```bash
# 验证 Token
gcloud secrets versions access latest \
  --secret mcp-bearer-token \
  --project ai-for-god
```

### ❌ Inspector 无法启动

```bash
# 更新依赖
npm install -g npm@latest
npm install -g @modelcontextprotocol/inspector

# 手动启动
mcp-inspector --config config/claude_desktop_config_cloud.json
```

## 监控和维护

### 查看实时日志

```bash
# 实时日志流
gcloud run services logs tail ministry-data-mcp --region us-central1

# 过滤错误
gcloud run services logs tail ministry-data-mcp --region us-central1 | grep ERROR
```

### 查看性能指标

访问 [Cloud Run 控制台](https://console.cloud.google.com/run/detail/us-central1/ministry-data-mcp/metrics?project=ai-for-god)

可以查看：
- 📊 请求量（QPS）
- ⏱️ 响应时间（P50, P95, P99）
- ❌ 错误率
- 💾 内存使用
- 🔢 实例数

### 更新部署

```bash
# 修改代码后重新部署
cd /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean
export GCP_PROJECT_ID=ai-for-god
export MCP_BEARER_TOKEN=REDACTED_SECRET
bash deploy/deploy-mcp.sh
```

## 最佳实践

1. ✅ **定期测试**: 部署后立即运行 `test_mcp_quick.sh`
2. ✅ **使用 Inspector**: 图形界面更容易调试
3. ✅ **查看日志**: 遇到问题先查看 Cloud Run 日志
4. ✅ **保护 Token**: 不要在公共仓库提交真实 Token
5. ✅ **监控性能**: 定期检查 Cloud Run 指标

## 配置 Claude Desktop

将以下内容复制到 Claude Desktop 配置：

**macOS/Linux**: `~/.config/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ministry-data": {
      "url": "https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer REDACTED_SECRET"
      }
    }
  }
}
```

重启 Claude Desktop 即可使用！

## 相关文档

- 📖 [快速入门](INSPECTOR_QUICKSTART.md) - 5 分钟上手
- 📖 [完整指南](docs/MCP_INSPECTOR_GUIDE.md) - 详细文档
- 📖 [API 文档](docs/API_ENDPOINTS.md) - 所有端点
- 📖 [部署指南](docs/MCP_CLOUD_RUN_DEPLOYMENT.md) - 如何部署
- 📖 [故障排除](docs/TROUBLESHOOTING.md) - 常见问题

## 获取帮助

### 查看帮助

```bash
# Inspector 帮助
npx @modelcontextprotocol/inspector --help

# 脚本帮助
bash inspect_cloud_mcp.sh --help
```

### 社区资源

- [MCP 官方文档](https://modelcontextprotocol.io)
- [MCP Inspector GitHub](https://github.com/modelcontextprotocol/inspector)
- [Google Cloud Run 文档](https://cloud.google.com/run/docs)

---

## 总结

✅ **测试脚本**: `bash test_mcp_quick.sh`  
✅ **图形界面**: `bash inspect_cloud_mcp.sh`  
✅ **命令行测试**: 使用 curl 命令  
✅ **Claude Desktop**: 配置后直接使用  

🎉 您的 MCP 服务器已完全就绪！

