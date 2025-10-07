# Ministry Data MCP Server - 完整指南

> **Model Context Protocol (MCP) Server** for Grace Irvine Ministry Data Management

## 🎯 快速开始

### 1️⃣ 运行测试脚本
```bash
# 快速检查所有配置
./test_mcp_connection.sh

# 详细测试服务器功能
python3 test_mcp_local.py
```

### 2️⃣ 重启 Claude Desktop
完全退出并重新启动 Claude Desktop 应用，让它加载新的 MCP 配置。

### 3️⃣ 在 Claude 中使用
1. 打开 Claude Desktop
2. 输入 `@` 查看可用工具
3. 选择 `ministry-data` 工具
4. 开始使用！

**示例：**
```
@ministry-data 获取最近5条讲道记录
@ministry-data 搜索所有讲员是王牧师的讲道
@ministry-data 查询10月份的志愿者安排
```

## 📁 重要文件说明

### 核心文件
- **`mcp_server.py`** - MCP 服务器主文件
- **`ministry-data.mcpb`** - MCP bundle 包（29.3 KB）
- **`manifest.json`** - 服务器配置清单

### 配置文件
- **`config/config.json`** - 应用配置
- **`config/service-account.json`** - Google Cloud 服务账号密钥

### Claude Desktop 配置
- **`~/Library/Application Support/Claude/claude_desktop_config.json`**

### 测试脚本
- **`test_mcp_connection.sh`** - 快速连接测试
- **`test_mcp_local.py`** - 详细功能测试
- **`test_mcp_server.sh`** - 服务器基础测试

## 📚 文档索引

### 快速参考
- **[MCP_TEST_RESULTS.md](MCP_TEST_RESULTS.md)** ⭐ 最新测试结果和状态
- **[MCP_LOCAL_TEST_GUIDE.md](MCP_LOCAL_TEST_GUIDE.md)** ⭐ 本地测试详细指南
- **[MCP_QUICK_REFERENCE.md](MCP_QUICK_REFERENCE.md)** - 工具快速参考

### 详细文档
- **[MCP_IMPLEMENTATION_SUMMARY.md](MCP_IMPLEMENTATION_SUMMARY.md)** - 实现细节
- **[MCP_SETUP_COMPLETE.md](MCP_SETUP_COMPLETE.md)** - 初始设置说明
- **[docs/MCP_DESIGN.md](docs/MCP_DESIGN.md)** - 设计文档
- **[docs/MCP_DEPLOYMENT.md](docs/MCP_DEPLOYMENT.md)** - 部署指南

## 🛠️ 可用工具清单

### 📖 数据获取（5个工具）
1. **get_sermon_data** - 获取讲道数据
   - 参数: `year` (可选), `limit` (可选)
   - 示例: "获取2025年的讲道记录"

2. **get_volunteer_data** - 获取志愿者数据
   - 参数: `year` (可选), `limit` (可选)
   - 示例: "获取本月的志愿者安排"

3. **get_volunteer_metadata** - 获取志愿者元数据
   - 参数: `year` (可选)
   - 示例: "获取所有志愿者的统计信息"

4. **get_person_service_history** - 获取个人服侍历史
   - 参数: `person_identifier` (必需), `year` (可选)
   - 示例: "查询张三的服侍历史"

5. **get_schedule_by_date** - 按日期获取安排
   - 参数: `date` (必需)
   - 示例: "获取10月13日的主日安排"

### 🔍 搜索工具（2个工具）
6. **search_sermons** - 搜索讲道
   - 参数: `query` (必需), `year` (可选)
   - 示例: "搜索关于祷告的讲道"

7. **search_volunteers** - 搜索志愿者记录
   - 参数: `query` (必需), `year` (可选)
   - 示例: "搜索招待组的志愿者"

### 📊 分析工具（2个工具）
8. **analyze_volunteer_availability** - 分析志愿者可用性
   - 参数: `start_date`, `end_date`, `role` (可选)
   - 示例: "分析10月份招待组的服侍情况"

9. **get_volunteer_stats** - 获取志愿者统计
   - 参数: `year` (可选), `role` (可选)
   - 示例: "统计2025年所有志愿者的服侍次数"

### 🔧 管理工具（3个工具）
10. **generate_service_layer** - 生成服务层数据
    - 参数: `domain` (sermon/volunteer), `year` (可选)
    - 示例: "生成2025年的sermon数据"

11. **validate_service_layer** - 验证服务层数据
    - 参数: `domain` (sermon/volunteer), `year` (可选)
    - 示例: "验证volunteer数据的完整性"

12. **clean_data** - 清洗原始数据
    - 参数: `source` (sermon/volunteer)
    - 示例: "清洗sermon原始数据"

## 💡 使用示例

### 示例 1: 查询讲道信息
```
用户: @ministry-data 获取最近的5条讲道记录

系统将：
1. 调用 get_sermon_data(limit=5)
2. 返回最新的5条讲道，包含：
   - 日期
   - 讲员姓名
   - 讲道主题
   - 经文
   - 音频链接（如有）
```

### 示例 2: 搜索特定讲员
```
用户: @ministry-data 搜索王牧师的所有讲道

系统将：
1. 调用 search_sermons(query="王牧师")
2. 返回所有王牧师的讲道记录
3. 按日期排序显示
```

### 示例 3: 分析志愿者服侍
```
用户: @ministry-data 分析张三在2025年的服侍情况

系统将：
1. 调用 get_person_service_history(person_identifier="张三", year="2025")
2. 统计服侍次数
3. 列出服侍的角色
4. 显示服侍日期和频率
```

### 示例 4: 查询主日安排
```
用户: @ministry-data 10月13日主日有哪些人服侍？

系统将：
1. 调用 get_schedule_by_date(date="2025-10-13")
2. 返回完整的主日安排：
   - 讲员
   - 司琴
   - 招待
   - 音控
   - 其他服侍人员
```

### 示例 5: 生成和验证数据
```
用户: @ministry-data 生成2025年的讲道服务层数据并验证

系统将：
1. 调用 generate_service_layer(domain="sermon", year="2025")
2. 从Google Sheets读取数据
3. 清洗和标准化数据
4. 生成JSON格式的服务层数据
5. 调用 validate_service_layer 验证数据质量
6. 返回生成报告
```

## 🔍 故障排查

### 问题：服务器无法连接
**症状：** 在 Claude 中看不到 ministry-data 工具

**检查步骤：**
```bash
# 1. 运行测试脚本
./test_mcp_connection.sh

# 2. 查看日志
tail -f ~/Library/Logs/Claude/mcp-server-ministry-data.log

# 3. 验证配置
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**解决方案：**
- 确保已重启 Claude Desktop
- 检查配置文件路径是否正确
- 验证 Python 环境
- 查看日志中的错误信息

### 问题：工具调用失败
**症状：** 工具可见但调用时出错

**检查步骤：**
```bash
# 测试服务器功能
python3 test_mcp_local.py

# 检查配置文件
ls -la config/config.json config/service-account.json
```

**解决方案：**
- 确保配置文件存在且格式正确
- 验证 Google Cloud 服务账号权限
- 检查 Google Sheets 访问权限
- 查看详细错误日志

### 问题：数据返回为空
**症状：** 工具调用成功但没有数据

**可能原因：**
- 指定的年份没有数据
- 服务层数据未生成
- Google Sheets 中没有数据
- 查询条件不匹配

**解决方案：**
```bash
# 生成服务层数据
python3 -c "
from scripts.service_layer import ServiceLayerManager
manager = ServiceLayerManager()
manager.generate_all_years(['2024', '2025', '2026'])
"
```

## 🔄 更新和维护

### 更新 MCPB Bundle
如果修改了代码，需要重新生成：
```bash
python3 << 'EOF'
import json
import zipfile
import os

files_to_include = [
    'mcp_server.py',
    'manifest.json',
    'icon.svg',
    'requirements.txt',
    'scripts/__init__.py',
    'scripts/service_layer.py',
    'scripts/gsheet_utils.py',
    'scripts/cloud_storage_utils.py',
    'scripts/cleaning_rules.py',
    'scripts/validators.py',
    'scripts/alias_utils.py',
    'config/config.example.json',
    'config/service-account.json',
    'config/config.json',
]

with zipfile.ZipFile('ministry-data.mcpb', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for file_path in files_to_include:
        if os.path.exists(file_path):
            zipf.write(file_path, file_path)

print("✅ MCPB updated")
EOF
```

### 更新配置
修改 `config/config.json` 后：
1. 不需要重新生成 MCPB
2. 只需重启 Claude Desktop

### 添加新工具
1. 在 `mcp_server.py` 中添加新的 `@server.call_tool` 处理器
2. 更新工具列表文档
3. 重新生成 MCPB
4. 重启 Claude Desktop

## 📊 系统架构

```
┌─────────────────────────────────────────────────┐
│           Claude Desktop Application            │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │         MCP Client (Built-in)             │ │
│  └───────────────┬───────────────────────────┘ │
└──────────────────┼─────────────────────────────┘
                   │ MCP Protocol (stdio)
                   │
┌──────────────────▼─────────────────────────────┐
│         ministry-data MCP Server               │
│              (mcp_server.py)                   │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │         Tool Handlers (12 tools)         │ │
│  └──────────────────┬───────────────────────┘ │
│                     │                          │
│  ┌──────────────────▼───────────────────────┐ │
│  │      ServiceLayerManager                 │ │
│  │      CleaningPipeline                    │ │
│  └──────────────────┬───────────────────────┘ │
└─────────────────────┼──────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼────────┐         ┌────────▼────────┐
│  Google Sheets │         │  Local Storage  │
│   (Raw Data)   │         │  (JSON Files)   │
└────────────────┘         └─────────────────┘
```

## 🎓 学习资源

### MCP 协议文档
- [MCP Official Documentation](https://modelcontextprotocol.io/)
- [MCP SDK for Python](https://github.com/modelcontextprotocol/python-sdk)

### 项目文档
- [Architecture](docs/ARCHITECTURE.md) - 系统架构
- [API Endpoints](docs/API_ENDPOINTS.md) - API 说明
- [Service Layer](docs/SERVICE_LAYER.md) - 服务层设计
- [Troubleshooting](docs/TROUBLESHOOTING.md) - 故障排查

## 📞 获取帮助

### 日志位置
```bash
# MCP Server 日志
~/Library/Logs/Claude/mcp-server-ministry-data.log

# 服务层日志
logs/service_layer/
```

### 运行诊断
```bash
# 快速诊断
./test_mcp_connection.sh

# 详细测试
python3 test_mcp_local.py

# 检查服务层数据
ls -la logs/service_layer/
```

### 常用命令
```bash
# 查看实时日志
tail -f ~/Library/Logs/Claude/mcp-server-ministry-data.log

# 测试服务器导入
python3 -c "import mcp_server; print('OK')"

# 验证配置
python3 -c "import json; print(json.load(open('config/config.json')))"

# 生成所有年份数据
python3 -c "from scripts.service_layer import ServiceLayerManager; ServiceLayerManager().generate_all_years(['2024','2025','2026'])"
```

## ✅ 检查清单

使用前确认：
- [ ] Python 3.12+ 已安装
- [ ] 所有依赖已安装 (`pip install -r requirements.txt`)
- [ ] 配置文件已设置 (`config/config.json`, `config/service-account.json`)
- [ ] Claude Desktop 配置已更新
- [ ] MCPB bundle 已生成 (`ministry-data.mcpb`)
- [ ] 测试脚本运行成功 (`./test_mcp_connection.sh`)
- [ ] Claude Desktop 已重启

## 🎉 开始使用

一切准备就绪！现在你可以：

1. 在 Claude Desktop 中输入 `@ministry-data` 开始使用
2. 尝试各种工具和查询
3. 查看文档了解更多功能
4. 遇到问题查看故障排查部分

祝使用愉快！🚀

