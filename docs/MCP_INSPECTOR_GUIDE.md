# MCP Inspector 使用指南

## 概述

MCP Inspector 是一个可视化工具，用于测试和调试 MCP (Model Context Protocol) 服务器。本指南介绍如何使用 MCP Inspector 检查已部署到 Google Cloud Run 的 MCP 服务器。

## 前提条件

- Node.js 和 npm 已安装
- 已部署 MCP 服务器到 Cloud Run
- 拥有有效的 Bearer Token

## 方法 1: 使用提供的脚本（推荐）

### 快速启动

```bash
# 使用默认配置
bash inspect_cloud_mcp.sh

# 或者自定义 URL 和 Token
MCP_URL=https://your-service-url.run.app \
MCP_TOKEN=your-bearer-token \
bash inspect_cloud_mcp.sh
```

### 脚本功能

脚本会自动：
1. ✅ 检查服务器健康状态
2. ✅ 创建临时配置文件
3. ✅ 启动 MCP Inspector
4. ✅ 在浏览器中打开交互界面
5. ✅ 退出时自动清理临时文件

## 方法 2: 使用 npx 直接连接

### SSE 模式（推荐用于 Cloud Run）

```bash
# 1. 创建配置文件
cat > mcp-inspector-config.json << 'EOF'
{
  "mcpServers": {
    "ministry-data-cloud": {
      "url": "https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30"
      }
    }
  }
}
EOF

# 2. 启动 Inspector
npx @modelcontextprotocol/inspector --config mcp-inspector-config.json
```

### HTTP 模式

如果 SSE 模式不可用，可以尝试 HTTP 模式：

```bash
cat > mcp-inspector-config.json << 'EOF'
{
  "mcpServers": {
    "ministry-data-cloud": {
      "url": "https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30"
      }
    }
  }
}
EOF

npx @modelcontextprotocol/inspector --config mcp-inspector-config.json
```

## 方法 3: 使用 curl 进行命令行测试

### 列出可用工具

```bash
curl -X POST https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp \
  -H "Authorization: Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }' | jq .
```

### 列出可用资源

```bash
curl -X POST https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp \
  -H "Authorization: Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "resources/list"
  }' | jq .
```

### 调用工具示例

```bash
# 查询下个主日的信息
curl -X POST https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp \
  -H "Authorization: Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "generate_weekly_preview",
      "arguments": {}
    }
  }' | jq .
```

### 读取资源示例

```bash
# 读取当前同工状态
curl -X POST https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp \
  -H "Authorization: Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "resources/read",
    "params": {
      "uri": "ministry://current/volunteer-status"
    }
  }' | jq .
```

## MCP Inspector 界面功能

### 1. 服务器信息面板
- 显示服务器 URL
- 显示连接状态
- 显示认证状态

### 2. 工具 (Tools) 面板
- 📋 列出所有可用工具
- 🔧 测试工具调用
- 📝 查看输入/输出 schema
- 🎯 实时查看工具执行结果

### 3. 资源 (Resources) 面板
- 📚 浏览所有可用资源
- 🔍 查看资源内容
- 📊 查看资源元数据
- 🔄 实时更新资源状态

### 4. 提示词 (Prompts) 面板
- 💬 查看预定义提示词
- ✏️ 测试提示词模板
- 🎨 自定义提示词参数

### 5. 日志 (Logs) 面板
- 📝 查看所有请求/响应
- ⚠️ 查看错误和警告
- 🔍 搜索和过滤日志
- 💾 导出日志数据

## 测试场景示例

### 场景 1: 查询下周主日安排

1. 在 Inspector 中选择 "Tools"
2. 找到 `generate_weekly_preview` 工具
3. 点击 "Execute"
4. 查看结果中的证道和同工信息

### 场景 2: 检查排班完整性

1. 选择 `check_upcoming_completeness` 工具
2. 设置 `weeks_ahead` 参数为 4
3. 执行并查看未来4周的空缺岗位

### 场景 3: 分析同工趋势

1. 选择 `analyze_volunteer_trends` 工具
2. 设置 `year` 参数为 "2025"
3. 查看活跃同工、休眠同工等统计

### 场景 4: 浏览资源

1. 切换到 "Resources" 面板
2. 点击 `ministry://current/next-sunday` 资源
3. 查看自动计算的下个主日数据

### 场景 5: 查看统计信息

1. 选择 `ministry://stats/summary` 资源
2. 查看整体统计数据
3. 导出数据用于报告

## 故障排除

### 问题 1: 无法连接到服务器

**症状**: Inspector 显示连接错误

**解决方案**:
```bash
# 1. 检查服务器健康状态
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/health

# 2. 验证 Bearer Token 是否正确
# 3. 检查网络连接
# 4. 查看 Cloud Run 日志
gcloud run services logs read ministry-data-mcp --region us-central1
```

### 问题 2: 认证失败

**症状**: 返回 "Invalid bearer token" 错误

**解决方案**:
1. 确认 Bearer Token 正确
2. 检查 Token 是否已过期
3. 验证 Cloud Run 服务的 secret 配置

```bash
# 查看 secret 配置
gcloud secrets versions access latest --secret mcp-bearer-token
```

### 问题 3: Inspector 无法启动

**症状**: npx 命令失败

**解决方案**:
```bash
# 1. 更新 npm
npm install -g npm@latest

# 2. 清除 npx 缓存
npx clear-npx-cache

# 3. 手动安装 Inspector
npm install -g @modelcontextprotocol/inspector

# 4. 使用全局安装的版本
mcp-inspector --config mcp-inspector-config.json
```

### 问题 4: SSE 连接超时

**症状**: SSE 连接建立后很快断开

**解决方案**:
- Cloud Run 默认请求超时为 300 秒
- 如需长连接，可以调整超时设置：

```bash
gcloud run services update ministry-data-mcp \
  --region us-central1 \
  --timeout 3600
```

## 高级用法

### 自定义配置

创建 `mcp-inspector-advanced.json`:

```json
{
  "mcpServers": {
    "ministry-data-cloud": {
      "url": "https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      },
      "timeout": 30000,
      "retries": 3,
      "retryDelay": 1000
    }
  },
  "logging": {
    "level": "debug",
    "output": "console"
  }
}
```

### 批量测试脚本

创建测试脚本 `test-mcp-tools.sh`:

```bash
#!/bin/bash

MCP_URL="https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp"
TOKEN="Bearer YOUR_TOKEN"

# 测试所有工具
TOOLS=(
  "query_volunteers_by_date"
  "query_sermon_by_date"
  "check_upcoming_completeness"
  "generate_weekly_preview"
  "analyze_role_coverage"
)

for tool in "${TOOLS[@]}"; do
  echo "Testing: $tool"
  curl -X POST "$MCP_URL" \
    -H "Authorization: $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"jsonrpc\": \"2.0\",
      \"id\": 1,
      \"method\": \"tools/call\",
      \"params\": {
        \"name\": \"$tool\",
        \"arguments\": {}
      }
    }" | jq '.result'
  echo "---"
done
```

## 性能监控

### 查看请求延迟

在 Cloud Run 控制台查看:
- 平均响应时间
- P50/P95/P99 延迟
- 请求量和错误率

### 查看实时日志

```bash
# 实时查看日志
gcloud run services logs tail ministry-data-mcp --region us-central1

# 过滤特定工具的日志
gcloud run services logs tail ministry-data-mcp --region us-central1 \
  | grep "query_volunteers"
```

## 最佳实践

1. **使用脚本**: 优先使用 `inspect_cloud_mcp.sh` 脚本，自动处理配置
2. **保护 Token**: 不要在公共仓库中提交包含真实 Token 的配置文件
3. **测试顺序**: 先测试简单工具，再测试复杂分析工具
4. **查看日志**: 遇到问题时先查看 Cloud Run 日志
5. **定期测试**: 部署后立即测试，确保所有功能正常

## 参考资源

- [MCP Inspector 官方文档](https://github.com/modelcontextprotocol/inspector)
- [MCP 协议规范](https://modelcontextprotocol.io)
- [Cloud Run 文档](https://cloud.google.com/run/docs)

## 支持

如有问题，请查看:
- `DEPLOYMENT_SUCCESS.md` - 部署信息
- `docs/TROUBLESHOOTING.md` - 故障排除
- Cloud Run 日志 - 运行时错误

