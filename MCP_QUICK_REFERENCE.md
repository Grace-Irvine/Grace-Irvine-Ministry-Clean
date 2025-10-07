# MCP Server 快速参考卡

## 🚀 启动命令

```bash
# HTTP 模式（推荐测试）
export MCP_REQUIRE_AUTH=false
python3 mcp_http_server.py

# stdio 模式（Claude Desktop）
python3 mcp_server.py
```

## 🔧 测试命令

```bash
# 健康检查
curl http://localhost:8080/health

# 列出工具
curl http://localhost:8080/mcp/tools

# 列出资源
curl http://localhost:8080/mcp/resources

# 列出提示词
curl http://localhost:8080/mcp/prompts

# 读取证道记录
curl -G http://localhost:8080/mcp/resources/read \
  --data-urlencode "uri=ministry://sermon/records"

# 调用清洗工具
curl -X POST http://localhost:8080/mcp/tools/clean_ministry_data \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

## 📦 5个工具 (Tools)

| 工具 | 功能 | 参数 |
|------|------|------|
| `clean_ministry_data` | 数据清洗 | dry_run, force |
| `generate_service_layer` | 生成服务层 | domains, generate_all_years |
| `validate_raw_data` | 数据校验 | check_duplicates, generate_report |
| `add_person_alias` | 添加别名 | alias, person_id, display_name |
| `get_pipeline_status` | 查询状态 | last_n_runs |

## 📚 10个资源 (Resources)

| URI | 说明 |
|-----|------|
| `ministry://sermon/records` | 所有证道记录 |
| `ministry://sermon/by-preacher/{name}` | 按讲员查询 |
| `ministry://sermon/series` | 讲道系列 |
| `ministry://volunteer/assignments` | 同工安排 |
| `ministry://volunteer/by-person/{id}` | 个人服侍记录 |
| `ministry://volunteer/availability/{month}` | 排班空缺 |
| `ministry://stats/summary` | 综合统计 |
| `ministry://stats/preachers` | 讲员统计 |
| `ministry://stats/volunteers` | 同工统计 |
| `ministry://config/aliases` | 别名配置 |

## 💬 5个提示词 (Prompts)

1. `analyze_preaching_schedule` - 分析讲道安排
2. `analyze_volunteer_balance` - 分析同工均衡
3. `find_scheduling_gaps` - 查找排班空缺
4. `check_data_quality` - 检查数据质量
5. `suggest_alias_merges` - 建议合并别名

## 🔐 鉴权

```bash
# 生成 Token
export MCP_BEARER_TOKEN=$(openssl rand -hex 32)

# 使用 Token
curl -H "Authorization: Bearer $MCP_BEARER_TOKEN" \
  http://localhost:8080/mcp/tools
```

## 🚢 部署

```bash
# 设置项目
export GCP_PROJECT_ID="your-project-id"
export MCP_BEARER_TOKEN=$(openssl rand -hex 32)

# 一键部署
./deploy-mcp-cloud-run.sh
```

## 📖 文档

- [快速开始](QUICKSTART_MCP.md) - 5分钟上手
- [完整部署](docs/MCP_DEPLOYMENT.md) - 详细指南
- [架构设计](docs/MCP_DESIGN.md) - 设计文档
- [安装完成](MCP_SETUP_COMPLETE.md) - 安装说明

## 🐛 故障排除

```bash
# 检查端口
lsof -i :8080

# 查看日志
tail -f logs/*.log

# 测试导入
python3 -c "import mcp_server; print('OK')"

# 重装依赖
pip3 install -r requirements.txt
```

## ✅ 检查清单

- [ ] 依赖已安装 (`pip3 install -r requirements.txt`)
- [ ] 服务器可启动 (`python3 mcp_http_server.py`)
- [ ] 健康检查通过 (`curl localhost:8080/health`)
- [ ] 工具列表正常 (`curl localhost:8080/mcp/tools`)
- [ ] 资源读取成功 (`curl localhost:8080/mcp/resources`)

---

**快速求助**: 查看 [MCP_SETUP_COMPLETE.md](MCP_SETUP_COMPLETE.md) 了解最新状态

