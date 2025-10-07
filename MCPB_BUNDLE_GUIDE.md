# MCP Bundle (.mcpb) 使用指南

## ✅ Bundle 已创建成功！

文件: **`ministry-data.mcpb`** (109.5 KB)

这是一个符合 [Anthropic MCPB 标准](https://github.com/anthropics/mcpb)的 MCP Bundle，可以一键安装到 Claude Desktop 和其他支持 MCP 的应用。

---

## 📦 Bundle 信息

- **名称**: ministry-data
- **版本**: 2.0.0
- **作者**: Grace Irvine Ministry
- **大小**: 109.5 KB（未打包: 671 KB）
- **文件数**: 38 个
- **Manifest 版本**: 0.2

### 包含的功能

#### 🔧 Tools (5个)
- `clean_ministry_data` - 数据清洗
- `generate_service_layer` - 生成服务层
- `validate_raw_data` - 数据校验
- `add_person_alias` - 添加别名
- `get_pipeline_status` - 查询状态

#### 📚 Resources (10个)
- 证道记录、讲员查询、系列信息
- 同工安排、个人记录、排班空缺
- 综合统计、讲员统计、同工统计
- 别名配置

#### 💬 Prompts (5个)
- 分析讲道安排
- 分析同工均衡
- 查找排班空缺
- 检查数据质量
- 建议合并别名

---

## 🚀 安装方式

### 方式 1: Claude Desktop（推荐）

1. **下载 Claude Desktop**
   - macOS/Windows: [https://claude.ai/download](https://claude.ai/download)

2. **双击安装**
   ```bash
   # 直接双击 ministry-data.mcpb 文件
   # 或在终端中运行：
   open ministry-data.mcpb
   ```

3. **配置必需文件**
   
   Claude 会提示你提供两个配置文件：
   
   - **Google Service Account JSON** (`config/service-account.json`)
     - 用于访问 Google Sheets
     - 从 GCP Console 下载
   
   - **Config JSON** (`config/config.json`)
     - 包含 Google Sheets URL 和设置
     - 参考 `config/config.example.json`

4. **开始使用**
   
   在 Claude 中输入：
   ```
   "请分析2024年的讲道安排"
   "查找10月份的排班空缺"
   "帮我清洗最新的数据"
   ```

### 方式 2: 手动配置（高级用户）

1. **解压 Bundle**
   ```bash
   mcpb unpack ministry-data.mcpb ~/ministry-data
   cd ~/ministry-data
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置文件**
   ```bash
   # 复制示例配置
   cp config/config.example.json config/config.json
   # 添加你的 service-account.json
   ```

4. **配置 Claude Desktop**
   
   编辑 `~/.config/Claude/claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "ministry-data": {
         "command": "python3",
         "args": ["~/ministry-data/mcp_server.py"],
         "env": {
           "GOOGLE_APPLICATION_CREDENTIALS": "~/ministry-data/config/service-account.json",
           "CONFIG_PATH": "~/ministry-data/config/config.json"
         }
       }
     }
   }
   ```

5. **重启 Claude Desktop**

---

## 📋 配置文件说明

### 1. service-account.json

Google Service Account 凭证，需要包含：
- `type`: "service_account"
- `project_id`: 你的 GCP 项目 ID
- `private_key_id`: 密钥 ID
- `private_key`: 私钥
- `client_email`: 服务账号邮箱

**获取方式**:
1. 访问 [GCP Console](https://console.cloud.google.com/)
2. IAM & Admin → Service Accounts
3. 创建或选择服务账号
4. Keys → Add Key → Create New Key → JSON

### 2. config.json

项目配置文件，参考 `config/config.example.json`:
```json
{
  "data_sources": {
    "raw_sheet_url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID",
    "raw_range": "Raw Data!A:Z",
    "clean_sheet_url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID",
    "clean_range": "Clean Data!A:Z",
    "aliases_sheet_url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID",
    "aliases_range": "Aliases!A:C"
  }
}
```

---

## 🔍 Bundle 内容

```
ministry-data.mcpb (109.5 KB)
├── manifest.json              # Bundle 元数据
├── mcp_server.py              # MCP Server 主文件
├── scripts/                   # 核心功能脚本
│   ├── clean_pipeline.py      # 数据清洗管线
│   ├── service_layer.py       # 服务层管理
│   ├── gsheet_utils.py        # Google Sheets 工具
│   └── ...                    # 其他工具
├── config/                    # 配置示例
│   ├── config.example.json
│   └── claude_desktop_config.example.json
├── logs/service_layer/        # 服务层数据缓存
├── requirements.txt           # Python 依赖
├── icon.svg                   # Bundle 图标
└── README.md                  # 项目说明
```

---

## 🛠️ 开发与更新

### 更新 Bundle

1. **修改代码**
   ```bash
   # 修改 mcp_server.py 或其他文件
   ```

2. **更新版本**
   ```bash
   # 编辑 manifest.json
   # 更新 "version": "2.0.1"
   ```

3. **重新打包**
   ```bash
   mcpb pack . ministry-data.mcpb
   ```

4. **验证 Bundle**
   ```bash
   mcpb validate manifest.json
   mcpb info ministry-data.mcpb
   ```

### 自定义配置

#### 修改 .mcpbignore

排除不需要打包的文件：
```
# 添加到 .mcpbignore
tests/
*.pyc
__pycache__/
.venv/
```

#### 修改 manifest.json

更新 Bundle 元数据：
```json
{
  "manifest_version": "0.2",
  "name": "your-bundle-name",
  "version": "1.0.0",
  "description": "Your description",
  "author": {
    "name": "Your Name",
    "url": "https://your-website.com"
  }
}
```

---

## 📊 文件大小优化

原始大小: **39.1 MB** (包含虚拟环境)  
优化后: **109.5 KB** ✅

### 优化技巧

1. **排除虚拟环境**
   ```
   .venv/
   venv/
   ```

2. **排除开发文件**
   ```
   tests/
   docs/
   *.md
   ```

3. **排除构建产物**
   ```
   __pycache__/
   *.pyc
   dist/
   build/
   ```

4. **排除大型日志**
   ```
   logs/*.log
   logs/*.csv
   ```

---

## ❓ 常见问题

### Q: Bundle 安装后无法运行？

**A**: 确保已提供配置文件：
- `config/service-account.json`
- `config/config.json`

### Q: Python 依赖未安装？

**A**: Bundle 使用系统 Python，确保已安装：
```bash
pip install -r requirements.txt
```

或者在 Claude Desktop 中，它会自动安装依赖。

### Q: 如何更新 Bundle？

**A**: 
1. 下载新版本的 `.mcpb` 文件
2. 双击安装（会覆盖旧版本）
3. 重启 Claude Desktop

### Q: 如何分享 Bundle？

**A**: 
- 直接发送 `ministry-data.mcpb` 文件
- 或上传到 GitHub Releases
- 或发布到 MCP Registry（如果可用）

### Q: Bundle 太大怎么办？

**A**: 检查 `.mcpbignore` 是否正确排除了：
- 虚拟环境 (`.venv/`)
- 测试文件
- 文档
- 日志文件

---

## 🔐 安全注意事项

⚠️ **重要**: 不要在 Bundle 中包含敏感信息：

- ❌ 不要包含 `service-account.json`
- ❌ 不要包含实际的 `config.json`
- ❌ 不要包含 API 密钥
- ❌ 不要包含密码或 Token

✅ **最佳实践**:
- 提供 `.example` 文件
- 在安装时要求用户提供配置
- 使用环境变量存储敏感信息

---

## 📚 相关资源

- [MCPB 官方仓库](https://github.com/anthropics/mcpb)
- [MCPB Manifest 规范](https://github.com/anthropics/mcpb/blob/main/MANIFEST.md)
- [MCP 协议文档](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai/download)

---

## 🎉 总结

✅ **成功创建 MCP Bundle!**

- 文件: `ministry-data.mcpb` (109.5 KB)
- 支持一键安装到 Claude Desktop
- 包含完整的 MCP Server 功能
- 优化的文件大小
- 符合 Anthropic MCPB 标准

**下一步**:
1. 双击 `ministry-data.mcpb` 在 Claude Desktop 中安装
2. 配置必需的 JSON 文件
3. 开始使用！

---

**创建时间**: 2025-10-07  
**Bundle 版本**: 2.0.0  
**MCPB CLI 版本**: 1.1.1

