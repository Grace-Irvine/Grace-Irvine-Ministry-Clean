# MCP Tools Optimization - 实施总结

**日期**: 2025-10-10  
**状态**: ✅ 已完成

## 问题描述

ChatGPT 在回答简单问题如 "本周主日都有哪些同工事工" 时，会不必要地调用管理工具（如 `sync_from_gcs`），而不是直接从 Cloud Storage 读取预生成的数据。

## 解决方案

将管理维护类工具从 MCP 接口中移除，仅保留查询工具。管理工具仍可通过 HTTP API 访问，供定时任务和管理员使用。

## 实施的变更

### 1. 移除 MCP 管理工具 (`mcp_server.py`)

**位置**: `handle_list_tools()` 函数

**移除的工具**:
- ❌ `clean_ministry_data` - 数据清洗
- ❌ `generate_service_layer` - 生成服务层
- ❌ `validate_raw_data` - 数据验证
- ❌ `sync_from_gcs` - 同步 GCS 数据

**保留的查询工具**:
- ✅ `query_volunteers_by_date` - 查询同工安排
- ✅ `query_sermon_by_date` - 查询证道信息
- ✅ `query_date_range` - 查询日期范围

### 2. 移除 MCP 管理提示词 (`mcp_server.py`)

**位置**: `handle_list_prompts()` 函数

**移除的提示词**:
- ❌ `check_data_quality` - 检查数据质量
- ❌ `suggest_alias_merges` - 建议别名合并

**保留的分析提示词**:
- ✅ `analyze_preaching_schedule` - 分析讲道安排
- ✅ `analyze_volunteer_balance` - 分析同工负担
- ✅ `find_scheduling_gaps` - 查找排班空缺

### 3. 保留 HTTP 端点访问

**位置**: `mcp_http_server.py` 和 `mcp_server.py` 中的 `handle_call_tool()`

所有管理工具的实现代码都保留在 `handle_call_tool()` 函数中，仍可通过 HTTP API 调用：

```bash
# 仍然可用 - 通过 HTTP API
POST /mcp/tools/clean_ministry_data
POST /mcp/tools/generate_service_layer
POST /mcp/tools/validate_raw_data
POST /mcp/tools/sync_from_gcs
```

## 数据访问架构

### ChatGPT 访问流程

```
ChatGPT 
  ↓ [MCP Bearer Token]
MCP Server (Cloud Run)
  ↓ [Service Account Credentials - 服务端配置]
Google Cloud Storage Bucket
  ↓
返回预生成的 JSON 数据
```

### 关键点

1. **ChatGPT 只需提供**: MCP Bearer Token（HTTP Authorization 头）
2. **ChatGPT 不需要提供**: GCS 凭证、服务账号密钥
3. **GCS 访问是服务端内部完成的**:
   - 服务账号凭证通过 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量配置
   - 或通过 Cloud Run Secret 挂载 `config/service-account.json`
   - 在 `mcp_server.py` 初始化时加载（第 60-83 行）

### 数据加载优先级

在 `load_service_layer_data()` 函数中（第 89-121 行）：

1. **优先**: 从 GCS Bucket 读取（第 95-101 行）
2. **回退**: 本地文件（仅在 GCS 失败时，第 103-120 行）

## 验证步骤

### 1. 验证 MCP 工具列表

```bash
# 使用 MCP 客户端或 HTTP 请求
GET /mcp/tools

# 应该只返回 3 个查询工具
```

预期结果:
```json
{
  "tools": [
    {"name": "query_volunteers_by_date", ...},
    {"name": "query_sermon_by_date", ...},
    {"name": "query_date_range", ...}
  ]
}
```

### 2. 验证查询工具直接读取 GCS

```bash
# 查询同工安排
POST /mcp
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "query_volunteers_by_date",
    "arguments": {"date": "2025-10-13"}
  }
}
```

检查日志应显示:
```
Loading volunteer data from GCS (version: latest)
Successfully loaded volunteer from GCS
```

### 3. 验证 HTTP 端点仍可访问管理工具

```bash
# 管理工具仍可通过 HTTP API 调用
POST /mcp/tools/sync_from_gcs
Authorization: Bearer <token>
{
  "domains": ["sermon", "volunteer"],
  "versions": ["latest"]
}
```

## 预期效果

### ChatGPT 使用体验

**之前**:
```
用户: 本周主日都有哪些同工事工？
ChatGPT: [调用 sync_from_gcs] → [调用 query_volunteers_by_date] → 返回结果
```

**之后**:
```
用户: 本周主日都有哪些同工事工？
ChatGPT: [直接调用 query_volunteers_by_date] → 返回结果
```

### 优势

1. ✅ **更快的响应**: 减少不必要的同步调用
2. ✅ **更简洁的工具列表**: ChatGPT 只看到相关的查询工具
3. ✅ **数据始终最新**: 由定时任务维护，查询时直接读取
4. ✅ **清晰的职责分离**: 
   - MCP = 查询接口（给 ChatGPT）
   - HTTP API = 管理接口（给 Cloud Run Jobs）

## 后续维护

### Cloud Run 定时任务配置

确保以下定时任务正常运行：

```yaml
# Cloud Scheduler Jobs
1. daily-clean-and-generate
   频率: 每天 2:00 AM
   目标: POST /mcp/tools/clean_ministry_data
        POST /mcp/tools/generate_service_layer
   
2. weekly-validation
   频率: 每周日 3:00 AM
   目标: POST /mcp/tools/validate_raw_data
```

### 手动触发（管理员）

```bash
# 设置认证
export MCP_TOKEN="your-bearer-token"
export MCP_URL="https://your-service.run.app"

# 清洗数据
curl -X POST "$MCP_URL/mcp/tools/clean_ministry_data" \
  -H "Authorization: Bearer $MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'

# 生成服务层
curl -X POST "$MCP_URL/mcp/tools/generate_service_layer" \
  -H "Authorization: Bearer $MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domains": ["sermon", "volunteer"], "generate_all_years": true}'
```

## 文件变更清单

| 文件 | 变更 | 说明 |
|------|------|------|
| `mcp_server.py` | 修改 `handle_list_tools()` | 移除 4 个管理工具 |
| `mcp_server.py` | 修改 `handle_list_prompts()` | 移除 2 个管理提示词 |
| `mcp_server.py` | 保留 `handle_call_tool()` | HTTP 端点仍可访问 |
| `mcp_http_server.py` | 无变更 | HTTP 路由继续工作 |

## 测试清单

- [ ] MCP 工具列表只显示 3 个查询工具
- [ ] 查询工具能正常从 GCS 读取数据
- [ ] HTTP API 仍能调用管理工具
- [ ] GCS 客户端初始化成功（检查日志）
- [ ] ChatGPT 能正常回答简单查询问题
- [ ] 定时任务能成功调用管理工具

## 相关文档

- `CHATGPT_CONNECTION_GUIDE.md` - ChatGPT 连接指南
- `docs/MCP_CLOUD_RUN_DEPLOYMENT.md` - Cloud Run 部署文档
- `docs/STORAGE.md` - GCS 存储配置

---

**实施人员**: Cursor AI Assistant  
**审核状态**: 待审核  
**部署状态**: 待部署到 Cloud Run

