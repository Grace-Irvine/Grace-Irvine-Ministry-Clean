# MCP Server 快速开始指南

5 分钟内启动并运行 MCP Server！

## 🚀 快速开始

### 方式 1: 本地 stdio 模式（推荐用于 Claude Desktop）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 测试运行
./test_mcp_server.sh
# 选择 1 (stdio mode)

# 3. 配置 Claude Desktop
# 编辑 ~/.config/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "ministry-data": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json",
        "CONFIG_PATH": "/path/to/config.json"
      }
    }
  }
}

# 4. 重启 Claude Desktop
```

### 方式 2: Cloud Run 远程部署

```bash
# 1. 设置环境变量
export GCP_PROJECT_ID="your-project-id"
export MCP_BEARER_TOKEN=$(openssl rand -hex 32)

# 2. 一键部署
./deploy-mcp-cloud-run.sh

# 3. 配置客户端（使用脚本输出的配置）
```

---

## 📝 使用示例

### 在 Claude Desktop 中使用

连接成功后，你可以：

```
你: "请分析2024年的讲道安排"

Claude 会自动：
1. 调用 Resources: ministry://sermon/records?year=2024
2. 调用 Resources: ministry://stats/preachers?year=2024
3. 生成分析报告
```

### 使用 curl 测试

```bash
# 列出所有工具
curl http://localhost:8080/mcp/tools

# 列出资源
curl http://localhost:8080/mcp/resources

# 读取证道记录
curl -G http://localhost:8080/mcp/resources/read \
  --data-urlencode "uri=ministry://sermon/records"

# 调用清洗工具
curl -X POST http://localhost:8080/mcp/tools/clean_ministry_data \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true, "force": false}'
```

### 使用 Python

```python
import requests

# 列出工具
response = requests.get("http://localhost:8080/mcp/tools")
tools = response.json()

# 调用工具
response = requests.post(
    "http://localhost:8080/mcp/tools/validate_raw_data",
    json={"check_duplicates": True, "generate_report": True}
)
result = response.json()
```

---

## 🔧 可用功能

### Tools（工具）- 执行操作

| 工具 | 说明 | 用途 |
|------|------|------|
| `clean_ministry_data` | 清洗原始数据 | 更新数据 |
| `generate_service_layer` | 生成领域数据 | 生成 JSON |
| `validate_raw_data` | 校验数据质量 | 质量检查 |
| `add_person_alias` | 添加别名 | 管理别名 |
| `get_pipeline_status` | 查询状态 | 监控系统 |

### Resources（资源）- 查询数据

| 资源 URI | 说明 |
|----------|------|
| `ministry://sermon/records` | 所有证道记录 |
| `ministry://sermon/by-preacher/{name}` | 按讲员查询 |
| `ministry://volunteer/assignments` | 同工安排 |
| `ministry://volunteer/by-person/{id}` | 某人的服侍记录 |
| `ministry://stats/summary` | 综合统计 |
| `ministry://config/aliases` | 别名映射 |

### Prompts（提示词）- 预设分析

| 提示词 | 说明 |
|--------|------|
| `analyze_preaching_schedule` | 分析讲道安排 |
| `analyze_volunteer_balance` | 分析同工均衡 |
| `find_scheduling_gaps` | 查找排班空缺 |
| `check_data_quality` | 检查数据质量 |
| `suggest_alias_merges` | 建议合并别名 |

---

## 🔐 安全配置

### 生成 Bearer Token

```bash
# 方式 1: openssl
openssl rand -hex 32

# 方式 2: Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 启用鉴权

```bash
# 设置环境变量
export MCP_REQUIRE_AUTH=true
export MCP_BEARER_TOKEN="your-secure-token"

# 重启服务
python3 mcp_http_server.py
```

### 使用鉴权的请求

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8080/mcp/tools
```

---

## 📊 常用命令

```bash
# 本地测试（HTTP 模式）
export MCP_REQUIRE_AUTH=false
python3 mcp_http_server.py

# 查看日志（Cloud Run）
gcloud run logs tail ministry-data-mcp --region us-central1

# 更新部署
./deploy-mcp-cloud-run.sh

# 测试健康
curl http://localhost:8080/health

# 获取能力
curl http://localhost:8080/mcp/capabilities
```

---

## 🐛 故障排除

### stdio 模式不工作

```bash
# 测试脚本是否能运行
python /absolute/path/to/mcp_server.py

# 查看 Claude Desktop 日志
tail -f ~/Library/Logs/Claude/mcp-server-ministry-data.log
```

### HTTP 模式连接失败

```bash
# 检查端口
lsof -i :8080

# 检查进程
ps aux | grep mcp_http_server

# 查看日志
tail -f logs/mcp_server.log
```

### Cloud Run 部署失败

```bash
# 检查镜像
gcloud container images list --repository=gcr.io/$GCP_PROJECT_ID

# 查看构建日志
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')

# 检查服务状态
gcloud run services describe ministry-data-mcp --region us-central1
```

---

## 📚 更多资源

- [完整部署指南](docs/MCP_DEPLOYMENT.md)
- [架构设计文档](docs/MCP_DESIGN.md)
- [API 端点文档](docs/API_ENDPOINTS.md)
- [MCP 官方文档](https://modelcontextprotocol.io/)

---

## 🎯 下一步

1. ✅ 完成基础配置
2. 📖 阅读 [MCP_DESIGN.md](docs/MCP_DESIGN.md) 了解架构
3. 🧪 使用 Prompts 进行数据分析
4. 🔧 根据需求自定义 Tools/Resources
5. 🚀 部署到生产环境

---

**需要帮助？** 查看 [常见问题](docs/MCP_DEPLOYMENT.md#常见问题) 或提交 Issue。

