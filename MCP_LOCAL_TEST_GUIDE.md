# MCP Server 本地测试指南

## 📋 概述

本指南帮助您在本地测试和使用 Ministry Data MCP 服务器。

## ✅ 已完成的配置

### 1. MCPB Bundle 文件
已创建 `ministry-data.mcpb` (29.3 KB)，包含：
- ✅ mcp_server.py (主服务器文件)
- ✅ manifest.json (服务器配置)
- ✅ icon.svg (服务器图标)
- ✅ requirements.txt (依赖项)
- ✅ scripts/ 目录下的所有服务层代码
- ✅ config/ 配置文件

### 2. Claude Desktop 配置
已更新 `~/Library/Application Support/Claude/claude_desktop_config.json`：

```json
{
  "preferences": {
    "menuBarEnabled": false
  },
  "mcpServers": {
    "ministry-data": {
      "command": "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
      "args": [
        "/Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean/mcp_server.py"
      ],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean/config/service-account.json",
        "CONFIG_PATH": "/Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean/config/config.json"
      }
    }
  }
}
```

## 🧪 测试步骤

### 步骤 1: 本地验证 MCP 服务器
运行测试脚本：
```bash
cd /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean
python3 test_mcp_local.py
```

应该看到：
```
✅ MCP server imported successfully
✅ Config file exists
✅ Service account exists
✅ ServiceLayerManager initialized
```

### 步骤 2: 重启 Claude Desktop
1. 完全退出 Claude Desktop 应用
2. 重新启动 Claude Desktop
3. 等待几秒钟让 MCP 服务器初始化

### 步骤 3: 检查日志
查看 MCP 服务器日志：
```bash
tail -f ~/Library/Logs/Claude/mcp-server-ministry-data.log
```

**成功的日志应该显示：**
```
[ministry-data] [info] Server started and connected successfully
[ministry-data] [info] Message from client: {"method":"initialize"...}
```

**如果看到错误：**
```
can't open file '//mcp_server.py': [Errno 2] No such file or directory
```
这表示路径配置有问题，请重新检查配置文件。

### 步骤 4: 在 Claude Desktop 中测试
1. 打开 Claude Desktop
2. 在对话框中输入 `@`
3. 应该看到 `ministry-data` 出现在工具列表中
4. 选择它并查看可用的工具：
   - `get_sermon_data` - 获取讲道数据
   - `get_volunteer_data` - 获取志愿者数据
   - `search_sermons` - 搜索讲道
   - `search_volunteers` - 搜索志愿者
   - `generate_service_layer` - 生成服务层数据
   - 等等...

### 步骤 5: 测试具体功能

#### 测试 1: 获取最近的讲道数据
```
@ministry-data 使用 get_sermon_data 工具获取最近10条讲道记录
```

#### 测试 2: 搜索特定讲员
```
@ministry-data 搜索 Pastor John 的所有讲道
```

#### 测试 3: 获取志愿者数据
```
@ministry-data 获取2025年10月的志愿者安排
```

#### 测试 4: 生成服务层数据
```
@ministry-data 生成2025年的讲道服务层数据
```

## 🔍 故障排查

### 问题 1: 服务器无法启动
**症状：** 日志显示 "can't open file" 错误

**解决方案：**
1. 检查 `claude_desktop_config.json` 中的路径是否正确
2. 确保使用绝对路径，不是相对路径
3. 验证 Python 解释器路径：
   ```bash
   which python3
   ```

### 问题 2: 找不到配置文件
**症状：** 日志显示配置文件不存在

**解决方案：**
1. 检查环境变量路径：
   ```bash
   ls -la /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean/config/
   ```
2. 确保 `config.json` 和 `service-account.json` 存在

### 问题 3: Google Sheets 认证失败
**症状：** 无法访问 Google Sheets 数据

**解决方案：**
1. 验证服务账号文件：
   ```bash
   cat config/service-account.json | jq .type
   ```
   应该显示 "service_account"
   
2. 确保服务账号有权限访问 Google Sheets
3. 检查 Sheet ID 在 config.json 中是否正确

### 问题 4: 依赖包缺失
**症状：** ImportError 或 ModuleNotFoundError

**解决方案：**
```bash
pip3 install -r requirements.txt
```

## 📊 可用的 MCP 工具

### 数据获取工具
1. **get_sermon_data** - 获取讲道数据
   - 参数: year (可选), limit (可选)
   
2. **get_volunteer_data** - 获取志愿者数据
   - 参数: year (可选), limit (可选)

3. **get_volunteer_metadata** - 获取志愿者元数据
   - 参数: year (可选)

### 搜索工具
4. **search_sermons** - 搜索讲道记录
   - 参数: query (必需), year (可选), limit (可选)
   
5. **search_volunteers** - 搜索志愿者记录
   - 参数: query (必需), year (可选), limit (可选)

### 数据分析工具
6. **analyze_volunteer_availability** - 分析志愿者可用性
   - 参数: start_date, end_date, role (可选)

7. **get_volunteer_stats** - 获取志愿者统计
   - 参数: year (可选), role (可选)

### 服务层生成工具
8. **generate_service_layer** - 生成服务层数据
   - 参数: domain (必需: sermon/volunteer), year (可选)

9. **validate_service_layer** - 验证服务层数据
   - 参数: domain (必需), year (可选)

### 数据清洗工具
10. **clean_data** - 清洗原始数据
    - 参数: source (必需: sermon/volunteer)

## 📝 使用示例

### 示例 1: 获取最近的讲道
```
请帮我获取最近5条讲道记录，我想看看最近的讲道主题。
```

### 示例 2: 分析志愿者服务情况
```
帮我分析一下2025年1月到3月的招待组志愿者服务情况。
```

### 示例 3: 搜索特定内容
```
搜索所有关于"祷告"主题的讲道。
```

### 示例 4: 生成服务层数据
```
为2025年生成讲道服务层数据，并验证数据质量。
```

## 🔧 维护和更新

### 更新 MCPB Bundle
如果修改了代码，需要重新生成 MCPB：
```bash
cd /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean
python3 << 'EOF'
import json
import zipfile
import os

with open('manifest.json', 'r') as f:
    manifest = json.load(f)

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
修改配置后无需重新生成 MCPB，只需重启 Claude Desktop。

## 📚 相关文档
- [MCP 快速参考](MCP_QUICK_REFERENCE.md)
- [MCP 实现摘要](MCP_IMPLEMENTATION_SUMMARY.md)
- [MCP 设计文档](docs/MCP_DESIGN.md)
- [故障排查指南](docs/TROUBLESHOOTING.md)

## 🆘 获取帮助
如果遇到问题：
1. 查看日志文件
2. 运行 `test_mcp_local.py` 测试脚本
3. 检查配置文件是否正确
4. 确保所有依赖包已安装

## ✨ 成功指标
- ✅ 日志中显示 "Server started and connected successfully"
- ✅ 在 Claude 中输入 @ 能看到 ministry-data 工具
- ✅ 能成功调用工具并获取数据
- ✅ 数据格式正确且完整

