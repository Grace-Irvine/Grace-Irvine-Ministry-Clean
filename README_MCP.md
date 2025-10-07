# MCP Server 集成说明

本项目已完整集成 MCP (Model Context Protocol) 支持！🎉

## 🚀 快速开始

### 选项 1: 本地使用（Claude Desktop）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 Claude Desktop
# 编辑 ~/.config/Claude/claude_desktop_config.json
# 参考: config/claude_desktop_config.example.json

# 3. 重启 Claude Desktop 即可使用
```

### 选项 2: 部署到 Cloud Run

```bash
# 1. 设置环境变量
export GCP_PROJECT_ID="your-project-id"
export MCP_BEARER_TOKEN=$(openssl rand -hex 32)

# 2. 一键部署
./deploy-mcp-cloud-run.sh

# 3. 使用远程 URL 连接
```

## 📖 文档

- **[5分钟快速开始](QUICKSTART_MCP.md)** - 最快上手指南
- **[完整部署指南](docs/MCP_DEPLOYMENT.md)** - 详细部署文档
- **[架构设计](docs/MCP_DESIGN.md)** - 设计理念与实现
- **[实施总结](MCP_IMPLEMENTATION_SUMMARY.md)** - 完整实施报告

## 🎯 主要功能

### Tools（工具）- 5个
执行操作、改变状态
```
clean_ministry_data      # 数据清洗
generate_service_layer   # 生成服务层
validate_raw_data        # 数据校验
add_person_alias         # 添加别名
get_pipeline_status      # 查询状态
```

### Resources（资源）- 10个
提供只读数据访问
```
ministry://sermon/records          # 证道记录
ministry://sermon/by-preacher/{n}  # 按讲员查询
ministry://volunteer/assignments   # 同工安排
ministry://stats/summary           # 综合统计
... 更多资源见文档
```

### Prompts（提示词）- 5个
预定义分析模板
```
analyze_preaching_schedule   # 分析讲道安排
analyze_volunteer_balance    # 分析同工均衡
find_scheduling_gaps         # 查找排班空缺
check_data_quality           # 检查数据质量
suggest_alias_merges         # 建议合并别名
```

## 🔧 测试

```bash
# 本地测试（stdio 或 HTTP）
./test_mcp_server.sh

# Python 客户端示例
python examples/mcp_client_example.py

# 手动测试端点
curl http://localhost:8080/mcp/tools
curl http://localhost:8080/mcp/resources
```

## 📁 新增文件

```
mcp_server.py                    # MCP Server 核心
mcp_http_server.py               # HTTP/SSE 传输层
deploy-mcp-cloud-run.sh          # 部署脚本
test_mcp_server.sh               # 测试脚本
docs/MCP_DEPLOYMENT.md           # 部署指南
QUICKSTART_MCP.md                # 快速开始
examples/mcp_client_example.py   # 客户端示例
config/claude_desktop_config.example.json
config/env.example
```

## 🔐 安全

生产环境务必：
- ✅ 设置 `MCP_BEARER_TOKEN`
- ✅ 启用 `MCP_REQUIRE_AUTH=true`
- ✅ 使用 Secret Manager
- ✅ 限制 CORS 来源
- ✅ 定期轮换 Token

## 🆘 需要帮助？

1. 查看 [QUICKSTART_MCP.md](QUICKSTART_MCP.md)
2. 查看 [常见问题](docs/MCP_DEPLOYMENT.md#常见问题)
3. 查看 [MCP 官方文档](https://modelcontextprotocol.io/)
4. 提交 GitHub Issue

## 🎓 更多信息

- **原有 FastAPI 应用仍然可用**：默认运行 `app.py`
- **MCP 模式独立运行**：设置 `MCP_MODE=http`
- **两种模式可以共存**：部署两个 Cloud Run 服务
- **完全向后兼容**：不影响现有 API

---

**MCP 版本**: 2.0.0  
**协议版本**: 2024-11-05  
**最后更新**: 2025-10-07

