# ChatGPT MCP 配置更新

## 问题诊断

❌ **原问题**: ngrok 转发到端口 8090，但 MCP Server 运行在端口 8080  
✅ **已修复**: ngrok 已重新配置为转发到端口 8080

## 新的 ngrok URL

```
https://cfdbe81cb308.ngrok-free.app
```

## ChatGPT GPT Action 配置

### 1. Schema 配置（不变）

保持原有的 OpenAPI Schema 配置，只需更新 Server URL。

### 2. Server URL（需要更新）

在 ChatGPT GPT Actions 设置中：

**旧 URL**:
```
https://2e3dfdd56609.ngrok-free.app
```

**新 URL**（请更新为）:
```
https://cfdbe81cb308.ngrok-free.app
```

### 3. Authentication（不变）

继续使用 Bearer Token 认证：
```
Bearer test-token
```

或者如果您设置了环境变量 `MCP_BEARER_TOKEN`，使用该值。

## 完整的 Actions Configuration

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Ministry Data MCP API",
    "version": "2.0.0"
  },
  "servers": [
    {
      "url": "https://cfdbe81cb308.ngrok-free.app"
    }
  ],
  "paths": {
    "/mcp/tools": {
      "get": {
        "operationId": "listTools",
        "summary": "List available MCP tools"
      }
    },
    "/mcp/tools/{tool_name}": {
      "post": {
        "operationId": "callTool",
        "summary": "Call a specific MCP tool",
        "parameters": [
          {
            "name": "tool_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object"
              }
            }
          }
        }
      }
    },
    "/mcp/resources": {
      "get": {
        "operationId": "listResources",
        "summary": "List available MCP resources"
      }
    },
    "/mcp/resources/read": {
      "get": {
        "operationId": "readResource",
        "summary": "Read a specific resource",
        "parameters": [
          {
            "name": "uri",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string"
            }
          }
        ]
      }
    },
    "/mcp/prompts": {
      "get": {
        "operationId": "listPrompts",
        "summary": "List available MCP prompts"
      }
    }
  }
}
```

## 验证步骤

### 1. 测试 ngrok 连接

```bash
curl https://cfdbe81cb308.ngrok-free.app/health
```

预期响应：
```json
{
  "status": "healthy",
  "timestamp": "2025-10-10T...",
  "auth_required": true
}
```

### 2. 测试认证

```bash
curl https://cfdbe81cb308.ngrok-free.app/mcp/tools \
  -H "Authorization: Bearer test-token"
```

应该返回 3 个查询工具的列表。

### 3. 测试提示词

```bash
curl https://cfdbe81cb308.ngrok-free.app/mcp/prompts \
  -H "Authorization: Bearer test-token"
```

应该返回 6 个提示词（包括新增的 3 个）。

## 在 ChatGPT 中更新配置

1. 打开您的 GPT 设置
2. 进入 "Actions" 部分
3. 找到现有的 MCP Action
4. 更新 Server URL 为: `https://cfdbe81cb308.ngrok-free.app`
5. 保存并测试

## 测试新功能

更新配置后，在 ChatGPT 中尝试：

1. **"下周日有哪些同工服侍？"**  
   应该调用 `analyze_next_sunday_volunteers` 提示词

2. **"分析最近4周同工在不同岗位的服侍"**  
   应该调用 `analyze_recent_volunteer_roles` 提示词

3. **"帮我分析2025年同工服侍频率"**  
   应该调用 `analyze_volunteer_frequency` 提示词

## 服务状态

- ✅ MCP HTTP Server: 运行中 (端口 8080)
- ✅ ngrok: 运行中 (转发到 8080)
- ✅ GCS 客户端: 已初始化
- ✅ 认证: Bearer Token
- ✅ 提示词: 6 个（3 个原有 + 3 个新增）

## 注意事项

### ngrok URL 会变化

每次重启 ngrok，URL 会改变。如果需要固定的 URL：

1. **选项 1**: 使用 ngrok 付费版获取固定域名
2. **选项 2**: 部署到 Cloud Run（推荐生产环境）
3. **选项 3**: 创建脚本自动更新 ChatGPT 配置

### 保持服务运行

当前服务以后台进程运行：
- MCP Server PID: 见 `ps aux | grep mcp_http_server`
- ngrok PID: 见 `ps aux | grep ngrok`
- 日志文件: `mcp_server.log` 和 `ngrok.log`

如果需要停止并重启：
```bash
# 停止
killall -9 Python ngrok

# 重启 MCP Server
python3 mcp_http_server.py > mcp_server.log 2>&1 &

# 重启 ngrok
ngrok http 8080 --log=stdout > ngrok.log 2>&1 &

# 获取新的 URL
grep -o 'https://[a-z0-9]*\.ngrok-free\.app' ngrok.log | head -1
```

---

**更新时间**: 2025-10-10  
**新 ngrok URL**: https://cfdbe81cb308.ngrok-free.app  
**状态**: ✅ 就绪

