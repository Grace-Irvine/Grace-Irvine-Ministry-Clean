# MCP Inspector 连接指南

MCP Inspector 是一个强大的调试工具，可以交互式地测试 MCP 服务器的工具、资源和提示词。

## 🚀 快速启动

### 方法 1: 使用启动脚本（推荐）

```bash
./start_mcp_inspector.sh
```

这会自动：
1. 启动 MCP Inspector
2. 连接到您的 Ministry Data MCP Server（stdio 模式）
3. 在浏览器中打开调试界面

### 方法 2: 手动启动

```bash
cd /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean
npx @modelcontextprotocol/inspector python3 mcp_server.py
```

### 方法 3: 连接到 HTTP Server（测试 HTTP 端点）

如果您想测试正在运行的 HTTP Server：

```bash
# 确保 MCP HTTP Server 正在运行
ps aux | grep mcp_http_server.py

# 启动 Inspector 连接到 HTTP 端点
npx @modelcontextprotocol/inspector \
  --transport http \
  --url http://localhost:8080/mcp
```

## 📋 MCP Inspector 功能

### 1. 测试工具 (Tools)

在 Inspector 中，您可以测试所有可用的查询工具：

- **query_volunteers_by_date**
  ```json
  {
    "date": "2025-10-13",
    "year": "2025"
  }
  ```

- **query_sermon_by_date**
  ```json
  {
    "date": "2025-10-13"
  }
  ```

- **query_date_range**
  ```json
  {
    "start_date": "2025-10-01",
    "end_date": "2025-10-31",
    "domain": "both"
  }
  ```

### 2. 查看资源 (Resources)

浏览所有可用的资源：

- `ministry://sermon/records` - 证道记录
- `ministry://volunteer/assignments` - 同工安排
- `ministry://stats/summary` - 统计摘要
- `ministry://stats/volunteers` - 同工统计
- `ministry://stats/preachers` - 讲员统计

### 3. 测试提示词 (Prompts)

测试所有 6 个提示词：

**原有提示词：**
1. `analyze_preaching_schedule` - 分析讲道安排
2. `analyze_volunteer_balance` - 分析同工负担
3. `find_scheduling_gaps` - 查找排班空缺

**新增提示词：**
4. `analyze_next_sunday_volunteers` - 分析下周日同工
5. `analyze_recent_volunteer_roles` - 分析最近几周同工岗位
6. `analyze_volunteer_frequency` - 分析同工服侍频率

## 🔍 使用场景

### 场景 1: 调试工具调用

测试查询工具是否正确返回数据：

1. 在 Inspector 中选择 "Tools" 标签
2. 选择 `query_volunteers_by_date`
3. 输入参数：`{"date": "2025-10-13"}`
4. 点击 "Call Tool"
5. 查看返回的 JSON 数据

### 场景 2: 验证数据源

检查 GCS 数据是否正确加载：

1. 选择 "Resources" 标签
2. 选择 `ministry://volunteer/assignments`
3. 点击 "Read Resource"
4. 验证返回的数据是否来自 GCS

### 场景 3: 测试新增的提示词

验证新增的提示词是否工作：

1. 选择 "Prompts" 标签
2. 选择 `analyze_next_sunday_volunteers`
3. 输入参数（可选）：`{"date": "2025-10-13"}`
4. 点击 "Get Prompt"
5. 查看生成的提示词文本

### 场景 4: 验证 ChatGPT 集成

模拟 ChatGPT 的调用流程：

1. 列出所有工具 → 验证只有 3 个查询工具
2. 调用 `query_volunteers_by_date` → 验证返回数据
3. 检查日志确认数据来自 GCS

## 🛠️ 高级配置

### 使用环境变量

如果需要设置特定的配置：

```bash
export CONFIG_PATH=/path/to/config.json
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

./start_mcp_inspector.sh
```

### 调试模式

启用详细日志：

```bash
export LOG_LEVEL=DEBUG
npx @modelcontextprotocol/inspector python3 mcp_server.py
```

### 连接到远程服务器

如果您的 MCP Server 部署在 Cloud Run：

```bash
npx @modelcontextprotocol/inspector \
  --transport http \
  --url https://your-service.run.app/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

## 📊 验证清单

使用 MCP Inspector 验证以下内容：

- [ ] **工具列表**: 只有 3 个查询工具（无管理工具）
- [ ] **提示词列表**: 有 6 个提示词（3 原有 + 3 新增）
- [ ] **数据源**: 数据从 GCS 加载（检查日志）
- [ ] **工具调用**: 查询工具返回正确数据
- [ ] **资源访问**: 可以读取所有资源
- [ ] **提示词生成**: 提示词包含正确的指令

## 🐛 常见问题

### Q1: Inspector 无法连接到服务器

**解决方案**：
```bash
# 检查 Python 路径
which python3

# 确保 mcp_server.py 可以直接运行
python3 mcp_server.py --help

# 检查依赖是否安装
pip3 list | grep mcp
```

### Q2: 工具调用返回错误

**解决方案**：
1. 检查 GCS 客户端是否初始化成功
2. 验证 `config/service-account.json` 存在
3. 查看服务器日志：`tail -f mcp_server.log`

### Q3: Inspector 显示旧的工具列表

**解决方案**：
```bash
# 停止所有 MCP Server 进程
killall -9 Python

# 重新启动 Inspector
./start_mcp_inspector.sh
```

### Q4: 无法读取 GCS 数据

**解决方案**：
```bash
# 检查 GCS 凭证
echo $GOOGLE_APPLICATION_CREDENTIALS
ls -la config/service-account.json

# 测试 GCS 连接
python3 -c "
from scripts.cloud_storage_utils import DomainStorageManager
manager = DomainStorageManager(
    bucket_name='grace-irvine-ministry-data',
    service_account_file='config/service-account.json'
)
data = manager.download_domain_data('volunteer', 'latest')
print(f'Records: {len(data.get(\"volunteers\", []))}')
"
```

## 🔗 相关工具

### 其他调试方法

1. **HTTP 直接测试**：
   ```bash
   curl http://localhost:8080/mcp/tools \
     -H "Authorization: Bearer test-token"
   ```

2. **Python REPL 测试**：
   ```python
   import asyncio
   import mcp_server
   
   # 列出工具
   tools = asyncio.run(mcp_server.handle_list_tools())
   print(f"Tools: {[t.name for t in tools]}")
   ```

3. **自动化测试**：
   ```bash
   python3 test_mcp_tools_optimization.py
   ```

## 📚 参考资源

- [MCP Inspector 文档](https://github.com/modelcontextprotocol/inspector)
- [MCP 协议规范](https://modelcontextprotocol.io)
- [项目 README](./README.md)
- [ChatGPT 连接指南](./CHATGPT_CONNECTION_GUIDE.md)

## 💡 提示

### 开发工作流

推荐的开发和调试流程：

1. **开发阶段**: 使用 MCP Inspector 测试新功能
2. **集成测试**: 使用自动化测试脚本验证
3. **部署前**: 通过 ngrok 在 ChatGPT 中测试
4. **生产环境**: 部署到 Cloud Run

### 快速命令

```bash
# 启动 Inspector
./start_mcp_inspector.sh

# 查看日志
tail -f mcp_server.log

# 运行测试
python3 test_mcp_tools_optimization.py

# 重启 HTTP Server
killall -9 Python && python3 mcp_http_server.py > mcp_server.log 2>&1 &
```

---

**最后更新**: 2025-10-10  
**版本**: 2.0.0  
**状态**: ✅ 就绪使用

