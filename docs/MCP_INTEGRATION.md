# MCP (Model Context Protocol) 集成指南

本文档介绍如何将教会主日事工数据清洗 API 集成到支持 MCP 的 AI 助手中。

## 📋 目录

- [什么是 MCP](#什么是-mcp)
- [API 端点](#api-端点)
- [MCP 工具定义](#mcp-工具定义)
- [集成示例](#集成示例)
- [使用场景](#使用场景)

## 什么是 MCP

Model Context Protocol (MCP) 是一个标准协议，允许 AI 助手（如 Claude、ChatGPT 等）通过 API 访问外部数据和服务。通过 MCP 集成，AI 助手可以：

- 查询教会主日事工数据
- 获取统计信息
- 触发数据清洗任务
- 分析和可视化事工安排

## API 端点

### 基础 URL

```
https://your-service-url.run.app
```

将 `your-service-url` 替换为你的 Cloud Run 服务 URL。

### 可用端点

#### 1. 健康检查

```http
GET /health
```

**响应示例：**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-06T10:00:00Z",
  "version": "1.0.0"
}
```

#### 2. 查询数据

```http
POST /api/v1/query
Content-Type: application/json
```

**请求体：**
```json
{
  "date_from": "2025-01-01",
  "date_to": "2025-12-31",
  "preacher": "张牧师",
  "limit": 50
}
```

**响应示例：**
```json
{
  "success": true,
  "count": 12,
  "data": [
    {
      "service_date": "2025-10-05",
      "sermon_title": "主里合一",
      "preacher_name": "张牧师",
      "scripture": "以弗所书 4:1-6",
      ...
    }
  ]
}
```

#### 3. 获取统计信息

```http
GET /api/v1/stats
```

**响应示例：**
```json
{
  "success": true,
  "stats": {
    "total_records": 150,
    "date_range": {
      "earliest": "2024-01-07",
      "latest": "2025-10-06"
    },
    "unique_preachers": 5,
    "unique_worship_leaders": 8,
    "last_updated": "2025-10-06T10:00:00Z"
  }
}
```

#### 4. 触发数据清洗

```http
POST /api/v1/clean
Content-Type: application/json
```

**请求体：**
```json
{
  "dry_run": false
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "清洗管线执行成功",
  "total_rows": 100,
  "success_rows": 95,
  "warning_rows": 3,
  "error_rows": 2,
  "timestamp": "2025-10-06T10:00:00Z",
  "preview_available": true
}
```

#### 5. 获取 MCP 工具定义

```http
GET /mcp/tools
```

**响应示例：**
```json
{
  "tools": [
    {
      "name": "query_ministry_data",
      "description": "查询教会主日事工数据",
      "inputSchema": { ... }
    },
    ...
  ]
}
```

## MCP 工具定义

API 提供以下 MCP 工具：

### 1. query_ministry_data

查询教会主日事工数据，支持多种过滤条件。

**参数：**
- `date_from` (string, 可选): 开始日期 (YYYY-MM-DD)
- `date_to` (string, 可选): 结束日期 (YYYY-MM-DD)
- `preacher` (string, 可选): 讲员名称（支持部分匹配）
- `limit` (integer, 可选): 返回记录数上限，默认 100

**示例：**
```javascript
{
  "tool": "query_ministry_data",
  "parameters": {
    "date_from": "2025-01-01",
    "preacher": "张牧师",
    "limit": 20
  }
}
```

### 2. get_ministry_stats

获取教会主日事工数据的统计信息。

**参数：** 无

**示例：**
```javascript
{
  "tool": "get_ministry_stats",
  "parameters": {}
}
```

### 3. trigger_data_cleaning

触发数据清洗任务，更新清洗后的数据。

**参数：**
- `dry_run` (boolean, 可选): 是否为测试模式（不写入 Google Sheets），默认 false

**示例：**
```javascript
{
  "tool": "trigger_data_cleaning",
  "parameters": {
    "dry_run": true
  }
}
```

## 集成示例

### Claude Desktop 配置

编辑 Claude Desktop 的配置文件 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "ministry-data": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "https://your-service-url.run.app/api/v1/query",
        "-H", "Content-Type: application/json",
        "-d", "@-"
      ]
    }
  }
}
```

### Python 客户端示例

```python
import requests

BASE_URL = "https://your-service-url.run.app"

def query_ministry_data(date_from=None, date_to=None, preacher=None, limit=100):
    """查询事工数据"""
    response = requests.post(
        f"{BASE_URL}/api/v1/query",
        json={
            "date_from": date_from,
            "date_to": date_to,
            "preacher": preacher,
            "limit": limit
        }
    )
    return response.json()

def get_stats():
    """获取统计信息"""
    response = requests.get(f"{BASE_URL}/api/v1/stats")
    return response.json()

def trigger_cleaning(dry_run=False):
    """触发数据清洗"""
    response = requests.post(
        f"{BASE_URL}/api/v1/clean",
        json={"dry_run": dry_run}
    )
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 查询 2025 年张牧师的讲道
    result = query_ministry_data(
        date_from="2025-01-01",
        date_to="2025-12-31",
        preacher="张牧师"
    )
    print(f"找到 {result['count']} 条记录")
    
    # 获取统计信息
    stats = get_stats()
    print(f"总记录数: {stats['stats']['total_records']}")
    
    # 测试运行清洗（不写入数据）
    cleaning_result = trigger_cleaning(dry_run=True)
    print(f"清洗结果: {cleaning_result['message']}")
```

### JavaScript 客户端示例

```javascript
const BASE_URL = 'https://your-service-url.run.app';

// 查询事工数据
async function queryMinistryData({ dateFrom, dateTo, preacher, limit = 100 }) {
  const response = await fetch(`${BASE_URL}/api/v1/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      date_from: dateFrom,
      date_to: dateTo,
      preacher,
      limit
    })
  });
  return response.json();
}

// 获取统计信息
async function getStats() {
  const response = await fetch(`${BASE_URL}/api/v1/stats`);
  return response.json();
}

// 触发数据清洗
async function triggerCleaning(dryRun = false) {
  const response = await fetch(`${BASE_URL}/api/v1/clean`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dry_run: dryRun })
  });
  return response.json();
}

// 使用示例
(async () => {
  // 查询数据
  const result = await queryMinistryData({
    dateFrom: '2025-01-01',
    preacher: '张牧师',
    limit: 20
  });
  console.log(`找到 ${result.count} 条记录`);
  
  // 获取统计
  const stats = await getStats();
  console.log(`总记录数: ${stats.stats.total_records}`);
})();
```

## 使用场景

### 1. AI 助手查询

**用户提问：**
> "查询 2025 年所有张牧师的讲道"

**AI 助手调用：**
```javascript
query_ministry_data({
  date_from: "2025-01-01",
  date_to: "2025-12-31",
  preacher: "张牧师"
})
```

### 2. 数据分析

**用户提问：**
> "分析一下今年的事工统计数据"

**AI 助手调用：**
```javascript
get_ministry_stats()
```

**AI 助手可以基于返回的数据进行分析：**
- 总共有多少次主日聚会
- 有哪些讲员参与
- 敬拜带领的人数
- 等等

### 3. 数据更新

**用户提问：**
> "更新一下最新的数据"

**AI 助手调用：**
```javascript
trigger_data_cleaning({ dry_run: false })
```

### 4. 智能排班助手

**用户提问：**
> "帮我看看 10 月份还有哪些周日没有安排敬拜带领"

**AI 助手可以：**
1. 调用 `query_ministry_data` 查询 10 月份的数据
2. 分析哪些日期的 `worship_lead_name` 为空
3. 提供建议

### 5. 讲道系列追踪

**用户提问：**
> "以弗所书系列的讲道进度如何？"

**AI 助手可以：**
1. 调用 `query_ministry_data` 查询相关系列
2. 统计已经讲了多少次
3. 显示覆盖的经文范围

## 测试 API

### 使用 curl

```bash
# 健康检查
curl https://your-service-url.run.app/health

# 查询数据
curl -X POST https://your-service-url.run.app/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": "2025-01-01",
    "limit": 10
  }'

# 获取统计
curl https://your-service-url.run.app/api/v1/stats

# 获取 MCP 工具定义
curl https://your-service-url.run.app/mcp/tools
```

### 使用 Postman 或 Insomnia

1. 导入 OpenAPI 文档：访问 `https://your-service-url.run.app/docs`
2. 创建请求并测试各个端点

## 安全考虑

1. **API 访问控制**：
   - 当前 API 为公开访问
   - 如需认证，可以添加 API Key 或 OAuth

2. **定时任务保护**：
   - `/trigger-cleaning` 端点需要 Bearer token
   - 只有 Cloud Scheduler 持有正确的 token

3. **速率限制**：
   - 建议在生产环境添加 API 速率限制
   - 可使用 Cloud Armor 或 API Gateway

4. **数据隐私**：
   - 确保服务账号只有必要的最小权限
   - 定期审查访问日志

## 故障排除

### API 返回 404

检查服务 URL 是否正确，确保服务已成功部署。

### API 返回 500

查看 Cloud Run 日志：
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-cleaning" --limit 50
```

### 数据未更新

检查 Cloud Scheduler 是否正常运行：
```bash
gcloud scheduler jobs describe ministry-cleaning-hourly --location=us-central1
```

### MCP 工具无法调用

1. 确认 AI 助手配置正确
2. 测试 API 端点是否可访问
3. 查看 AI 助手的日志输出

## 支持

如有问题或建议，请联系项目维护者或提交 Issue。

