# 教会主日事工数据管理系统 (v3.4)

一个完整的教会主日事工数据管理系统，支持数据清洗、服务层转换、RESTful API 访问，以及 **AI 助手集成（MCP 协议）**。

## ✨ 最新更新 (v3.4)

**🔄 MCP服务器统一实现** (2025-10-10)

- ✅ **单一文件实现**：stdio 和 HTTP/SSE 模式统一在 `mcp_local/mcp_server.py` 中
- ✅ **自动模式切换**：根据环境变量（PORT）自动选择运行模式
- ✅ **完全兼容**：支持 Claude Desktop（stdio）和 ChatGPT/OpenAI（HTTP/SSE）
- ✅ **简化部署**：单一Docker镜像，统一配置

👉 **查看 [MCP本地文档](mcp_local/README.md)** | **[更新日志](CHANGELOG.md)**

## 🎉 核心特性

### 🤖 AI 助手集成（MCP协议）
- **自然语言查询**：用对话方式查询和分析数据
- **多客户端支持**：Claude Desktop（本地）+ ChatGPT/OpenAI（云端）
- **9个工具**：数据清洗、查询、分析、生成服务层
- **22个资源**：证道数据、同工数据、统计信息
- **12个提示词**：预定义分析模板

### 📊 数据管理
- **智能清洗**：日期标准化、文本清理、别名映射、数据校验
- **服务层**：转换为sermon和volunteer领域模型
- **云存储**：自动上传到Google Cloud Storage
- **变化检测**：SHA-256哈希，仅在数据变化时执行

### ☁️ 云端部署
- **RESTful API**：完整的数据查询和管理接口
- **Cloud Run**：自动扩展，按需付费
- **定时任务**：Cloud Scheduler自动更新数据

## 🏗️ 架构概览

本系统采用**单一仓库（Monorepo）**架构，通过清晰的目录结构实现了**API服务**和**MCP服务**的职责分离：

```
├── api/          # API服务 - 数据清洗和管理（FastAPI）
├── mcp/          # MCP服务 - AI助手集成（MCP协议）
├── core/         # 共享核心业务逻辑（80%+代码重用）
└── deploy/       # 独立部署脚本
```

**两个独立服务**:
- 🔵 **API Service** (`ministry-data-api`) - 数据清洗、REST API、统计分析
- 🟢 **MCP Service** (`ministry-data-mcp`) - AI助手集成、MCP协议、自然语言查询

**独立部署** → 各自的Dockerfile → 独立Cloud Run服务 → 共享core/逻辑

👉 **详细架构说明**: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 📚 文档导航

### 快速开始
- 📖 [5分钟快速上手](docs/QUICKSTART.md) - 新用户必读
- 🏗️ [系统架构](docs/ARCHITECTURE.md) - 架构设计文档
- 📝 [更新日志](CHANGELOG.md) - 版本历史

### AI 助手集成（MCP）
- 🤖 [MCP服务器文档](mcp_local/README.md) - 完整使用指南
- 🔍 [MCP Inspector使用指南](docs/MCP_INSPECTOR.md) - Inspector调试工具
- 🎯 [同工分析提示词](VOLUNTEER_ANALYSIS_PROMPTS.md) - AI分析示例
- 🏗️ [MCP架构设计](docs/MCP_DESIGN.md) - 详细设计方案
- ☁️ [MCP云端部署](docs/MCP_DEPLOYMENT.md) - Cloud Run部署

### API服务
- 🔵 [API服务文档](api/README.md) - REST API说明
- 📚 [API端点文档](docs/API_ENDPOINTS.md) - 完整端点列表
- 📦 [服务层架构](docs/SERVICE_LAYER.md) - 领域模型设计

### 数据管理
- 🔄 [自动别名同步](docs/AUTO_ALIAS_SYNC.md) - 自动识别和管理同工名字
- 📋 [Schema管理](docs/SCHEMA_MANAGEMENT.md) - 动态列映射和部门管理

### 部署和运维
- ☁️ [云端部署指南](docs/DEPLOYMENT.md) - Cloud Run + Scheduler
- 💾 [存储管理](docs/STORAGE.md) - Cloud Storage配置
- 🚀 [常用命令](docs/QUICK_COMMANDS.md) - 命令速查
- 🔧 [故障排除](docs/TROUBLESHOOTING.md) - 问题解决

## 📋 目录

- [特性](#特性)
- [快速开始](#快速开始)
- [本地调试](#本地调试)（🔥 新增）
- [配置说明](#配置说明)
- [使用方式](#使用方式)
- [数据清洗规则](#数据清洗规则)
- [输出 Schema](#输出-schema)
- [测试](#测试)
- [故障排除](#故障排除)

## ✨ 特性

### 🤖 MCP 集成（v3.0 新增）
- **🔌 AI 助手集成**：通过 MCP 协议支持 Claude Desktop、ChatGPT 等 AI 助手
- **💬 自然语言交互**：用对话方式查询和分析数据，无需编写代码
- **🛠️ 5 个 Tools**：执行数据清洗、生成服务层、验证数据、管理别名
- **📦 10 个 Resources**：提供证道、同工、统计数据的结构化访问
- **💡 5 个 Prompts**：预定义分析模板，引导 AI 进行常见分析任务
- **🔀 双传输模式**：stdio（本地）+ HTTP/SSE（远程）
- **📦 MCPB 打包**：一键安装到 Claude Desktop

### 核心清洗功能
- **可配置的清洗规则**：通过 JSON 配置文件管理所有清洗规则
- **人名别名映射**：支持将多个别名（中文名、英文名、昵称）映射到统一的人员 ID
- **多种日期格式支持**：自动识别并标准化多种日期格式
- **智能文本清理**：去除空白、处理占位符、标准化空格
- **歌曲拆分与去重**：支持多种分隔符，自动去重
- **数据校验**：生成详细的错误和警告报告
- **Dry-run 模式**：可先预览清洗结果，不写回 Google Sheet

### 服务层（v2.0）
- **📦 领域模型**：Sermon Domain（证道域）+ Volunteer Domain（同工域）
- **🔄 多年份支持**：自动生成所有历史年份数据（2024-2026）
- **💾 Cloud Storage**：自动上传到 Google Cloud Storage
- **📁 智能组织**：按领域和年份组织文件（latest + yearly）

### 云端部署（v2.0）
- **☁️ Cloud Run 部署**：一键部署到 Google Cloud Run
- **⏰ 智能定时任务**：每30分钟自动检测并更新（仅在数据变化时执行）
- **🔍 变化检测**：SHA-256哈希比对，无变化时< 1秒返回
- **🚀 RESTful API**：完整的数据查询和管理接口
- **🔒 安全认证**：Bearer Token 保护敏感端点
- **📊 实时统计**：动态数据统计和分析

### 技术亮点
- **详细日志**：记录所有操作和问题
- **💰 成本友好**：基本在 Google Cloud 免费额度内（~$1.00/月）
- **⚡ 高性能**：智能跳过、并行处理、增量更新
- **🤖 AI 原生**：为 AI 集成设计的 MCP 协议支持

## 🚀 快速开始

### 方式 1：AI 助手集成（推荐）🤖

通过 MCP 协议与 Claude Desktop 或 ChatGPT 集成：

```bash
# Claude Desktop 本地模式
python mcp_local/mcp_server.py

# 或部署到Cloud Run（HTTP模式）
./deploy/deploy-mcp.sh
```

**特点**：自然语言查询、多客户端支持、预定义分析模板

👉 **详细说明**: [MCP服务器文档](mcp_local/README.md)

---

### 方式 2：本地数据清洗

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置服务账号
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# 3. 编辑配置文件
vim config/config.json

# 4. 干跑模式测试
python core/clean_pipeline.py --config config/config.json --dry-run

# 5. 正式运行
python core/clean_pipeline.py --config config/config.json
```

👉 **详细说明**: [快速上手指南](docs/QUICKSTART.md)

---

### 方式 3：云端部署

部署 API 服务和 MCP 服务到 Google Cloud Run：

```bash
# 设置项目ID
export GCP_PROJECT_ID=your-project-id

# 部署所有服务
./deploy/deploy-all.sh
```

**特点**：自动扩展、定时任务、低成本（~$1/月）

👉 **详细说明**: [云端部署指南](docs/DEPLOYMENT.md)

## 🔧 本地调试

### 为什么需要本地调试？

在配置 Google Sheets 之前，建议先用本地 Excel 文件调试：
- ✅ **无需配置服务账号**：直接使用本地文件
- ✅ **快速迭代**：修改-测试-修改，循环更快
- ✅ **生成别名表**：自动提取所有人名
- ✅ **验证清洗逻辑**：确保规则正确

### 快速开始（3 步）

#### 1. 提取人名，生成别名表

```bash
python3 scripts/extract_aliases_smart.py \
    --excel "tests/你的Excel文件.xlsx" \
    -o tests/generated_aliases.csv
```

**输出**：`tests/generated_aliases.csv` - 包含所有提取的人名

#### 2. 编辑别名表

打开 `tests/generated_aliases.csv`，合并同一人的不同写法：

```csv
# 示例：合并"华亚西"和"亚西"
alias,person_id,display_name,count,note
华亚西,person_huayaxi,华亚西,18,
亚西,person_huayaxi,华亚西,13,    ← 改为相同的 person_id
```

#### 3. 本地测试清洗

```bash
python3 scripts/debug_clean_local.py \
    --excel "tests/你的Excel文件.xlsx" \
    --aliases tests/generated_aliases.csv \
    -o tests/debug_output.csv
```

**输出**：
- `tests/debug_output.csv` - 清洗后的数据
- `tests/debug_output.json` - JSON 格式
- 控制台显示校验报告

### 详细文档

- 📖 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - 故障排除指南

---

## ⚙️ 配置说明

### 配置文件结构

`config/config.json` 包含以下部分：

#### 1. source_sheet（原始表）
```json
{
  "url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
  "range": "RawData!A1:Z"
}
```

#### 2. target_sheet（清洗层）
```json
{
  "url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
  "range": "CleanData!A1"
}
```

#### 3. columns（列名映射）
将原始表的中文列名映射到标准英文列名：
```json
{
  "service_date": "主日日期",
  "sermon_title": "讲道标题",
  "preacher": "讲员",
  ...
}
```

#### 4. cleaning_rules（清洗规则）
```json
{
  "date_format": "YYYY-MM-DD",
  "strip_spaces": true,
  "split_songs_delimiters": ["、", ",", "/", "|"],
  "merge_columns": {
    "worship_team": ["worship_team_1", "worship_team_2"]
  }
}
```

#### 5. alias_sources（别名数据源）
```json
{
  "people_alias_sheet": {
    "url": "https://docs.google.com/spreadsheets/d/YOUR_ALIAS_SHEET_ID/edit",
    "range": "PeopleAliases!A1:C"
  }
}
```

别名表格式（3列）：
| alias | person_id | display_name |
|-------|-----------|--------------|
| 张牧师 | preacher_zhang | 张牧师 |
| Pastor Zhang | preacher_zhang | 张牧师 |
| 王丽 | person_wangli | 王丽 |

## 📖 使用方式

### 基本用法

#### 方式 1：使用便捷脚本（推荐）

```bash
# 运行测试
./run_pipeline.sh --test

# 干跑模式
./run_pipeline.sh --dry-run

# 正式运行
./run_pipeline.sh

# 使用自定义配置
./run_pipeline.sh --config path/to/config.json --dry-run
```

#### 方式 2：直接使用 Python

```bash
# 使用默认配置
python scripts/clean_pipeline.py

# 指定配置文件
python scripts/clean_pipeline.py --config path/to/config.json

# 干跑模式
python scripts/clean_pipeline.py --dry-run
```

### 输出文件

运行后会生成以下文件：

- `logs/clean_preview.csv` - 清洗后数据的 CSV 预览
- `logs/clean_preview.json` - 清洗后数据的 JSON 预览
- `logs/validation_report_YYYYMMDD_HHMMSS.txt` - 详细校验报告

## 🧹 数据清洗规则

### 1. 日期标准化
- **输入格式**：`2025/10/05`, `2025年10月5日`, `10/05/2025`
- **输出格式**：`2025-10-05`

### 2. 文本清理
- 去除首尾空格（包括全角空格 `　`）
- 多个空格合并为一个
- 占位符处理：`-`, `N/A`, `无`, `—` → 空字符串

### 3. 人名别名映射
- 将多个别名映射到统一的 `person_id` 和显示名
- 不区分大小写
- 忽略空白字符

### 4. 歌曲拆分
- 支持多种分隔符：`、`, `,`, `/`, `|`
- 自动去重
- 去除首尾空格

### 5. 经文引用标准化
- 在书名和章节之间添加空格
- 示例：`以弗所书4:1-6` → `以弗所书 4:1-6`

### 6. 列合并
- 将多列合并为列表（如 `worship_team_1` + `worship_team_2`）
- 自动过滤空值
- 去重

## 📊 输出 Schema

清洗后的数据包含以下字段（固定顺序）：

```
service_date          主日日期 (YYYY-MM-DD)
service_week          服务周数 (1-53)
service_slot          服务时段 (morning/noon/evening)
sermon_title          讲道标题
series                讲道系列
scripture             经文
preacher_id           讲员 ID
preacher_name         讲员姓名
catechism             要理问答
reading               读经
worship_lead_id       敬拜带领 ID
worship_lead_name     敬拜带领姓名
worship_team_ids      敬拜同工 ID 列表 (JSON)
worship_team_names    敬拜同工姓名列表 (JSON)
pianist_id            司琴 ID
pianist_name          司琴姓名
songs                 诗歌列表 (JSON)
audio_id              音控 ID
audio_name            音控姓名
video_id              导播/摄影 ID
video_name            导播/摄影姓名
propresenter_play_id  ProPresenter播放 ID
propresenter_play_name ProPresenter播放姓名
propresenter_update_id ProPresenter更新 ID
propresenter_update_name ProPresenter更新姓名
assistant_id          助教 ID
assistant_name        助教姓名
notes                 备注
source_row            原始表行号
updated_at            更新时间 (ISO 8601)
```

## 🧪 测试

### 运行单元测试

```bash
# 运行所有测试
pytest tests/test_cleaning.py -v

# 运行特定测试类
pytest tests/test_cleaning.py::TestCleaningRules -v

# 运行特定测试方法
pytest tests/test_cleaning.py::TestCleaningRules::test_clean_date_formats -v
```

### 测试覆盖

单元测试涵盖：
- ✅ 日期格式清洗和标准化
- ✅ 文本清理（空格、占位符）
- ✅ 经文引用标准化
- ✅ 歌曲拆分与去重
- ✅ 列合并
- ✅ 人名别名映射
- ✅ 数据校验（必填字段、日期有效性、重复检测）

### 样例数据

`tests/sample_raw.csv` 包含多种测试场景：
- 不同日期格式
- 带空格的文本
- 多种歌曲分隔符
- 人名别名
- 空值和占位符
- 无效日期（用于测试错误处理）

## 📝 样例：从原始到清洗

### 原始数据（一行）

```
主日日期: 2025/10/05
讲道标题: 主里合一
经文: 以弗所书 4:1-6
讲员: 张牧师
讲道系列: 以弗所书系列
要理问答: 第37问
读经: 诗篇133
敬拜带领: 王丽
敬拜同工1: 陈明
敬拜同工2: 林芳
司琴: 李伟
詩歌: 奇异恩典 / 我心灵得安宁
音控: 赵强
导播/摄影: 周晨
ProPresenter播放: 黄立
ProPresenter更新: 李慧
助教: 刘丹
```

### 清洗后数据（JSON 格式）

```json
{
  "service_date": "2025-10-05",
  "service_week": 41,
  "service_slot": "morning",
  "sermon_title": "主里合一",
  "series": "以弗所书系列",
  "scripture": "以弗所书 4:1-6",
  "preacher_id": "preacher_zhang",
  "preacher_name": "张牧师",
  "catechism": "第37问",
  "reading": "诗篇 133",
  "worship_lead_id": "person_wangli",
  "worship_lead_name": "王丽",
  "worship_team_ids": "[\"person_chenming\",\"person_linfang\"]",
  "worship_team_names": "[\"陈明\",\"林芳\"]",
  "pianist_id": "person_liwei",
  "pianist_name": "李伟",
  "songs": "[\"奇异恩典\",\"我心灵得安宁\"]",
  "audio_id": "person_zhaoqiang",
  "audio_name": "赵强",
  "video_id": "person_zhouchen",
  "video_name": "周晨",
  "propresenter_play_id": "person_huangli",
  "propresenter_play_name": "黄立",
  "propresenter_update_id": "person_lihui",
  "propresenter_update_name": "李慧",
  "assistant_id": "person_liudan",
  "assistant_name": "刘丹",
  "notes": "",
  "source_row": 2,
  "updated_at": "2025-10-06T10:00:00Z"
}
```

## 🔒 安全与权限

### 最小权限原则

- ✅ 原始表：只读（Viewer）权限
- ✅ 清洗表：只写对应范围
- ✅ 别名表：只读（Viewer）权限

### 敏感信息保护

- ❌ **不要**将服务账号 JSON 文件提交到代码仓库
- ✅ 使用 `.gitignore` 排除 `*.json`（除了 `config/config.json`）
- ✅ 使用环境变量 `GOOGLE_APPLICATION_CREDENTIALS`
- ❌ 日志中不打印敏感令牌

## 🔧 故障排除

### 问题：无法读取 Google Sheet

**错误**：`HttpError 403: Permission denied`

**解决**：
1. 确认服务账号有权限访问对应的 Sheet
2. 在 Sheet 中添加服务账号邮箱（如 `xxx@xxx.iam.gserviceaccount.com`）为协作者
3. 检查 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量是否正确设置

### 问题：日期格式无法识别

**解决**：
- 检查原始数据的日期格式
- 如有特殊格式，可在 `cleaning_rules.py` 的 `clean_date()` 方法中添加正则表达式

### 问题：别名映射不生效

**解决**：
1. 确认别名表的列名为：`alias`, `person_id`, `display_name`
2. 检查别名表中是否有相应的映射记录
3. 注意别名匹配不区分大小写且忽略空白

### 问题：清洗后有大量错误行

**解决**：
1. 查看 `logs/validation_report_*.txt` 了解具体错误
2. 检查原始数据是否符合预期格式
3. 根据错误信息调整 `config.json` 中的配置

## 📂 项目结构

```
Grace-Irvine-Ministry-Clean/
│
├── api/                         # 🔵 API服务（数据清洗和管理）
│   ├── app.py                   # FastAPI应用主文件
│   ├── Dockerfile               # API服务专用Dockerfile
│   ├── __init__.py              # Python包标识
│   └── README.md                # API服务文档
│
├── mcp/                         # 🟢 MCP服务（AI助手集成）
│   ├── mcp_server.py            # stdio模式服务器
│   ├── mcp_http_server.py       # HTTP/SSE模式服务器
│   ├── Dockerfile               # MCP服务专用Dockerfile
│   ├── __init__.py              # Python包标识
│   └── README.md                # MCP服务文档
│
├── core/                        # 🔧 共享核心业务逻辑
│   ├── __init__.py
│   ├── clean_pipeline.py        # 主清洗管线
│   ├── service_layer.py         # 服务层转换器
│   ├── gsheet_utils.py          # Google Sheets 工具
│   ├── cleaning_rules.py        # 清洗规则
│   ├── validators.py            # 数据校验器
│   ├── alias_utils.py           # 别名映射工具
│   ├── cloud_storage_utils.py   # Cloud Storage 工具
│   └── change_detector.py       # 变化检测
│
├── deploy/                      # 📦 部署脚本
│   ├── deploy-api.sh            # API服务部署
│   ├── deploy-mcp.sh            # MCP服务部署
│   └── deploy-all.sh            # 统一部署脚本
│
├── config/                      # ⚙️ 配置文件
│   ├── config.json              # 主配置文件
│   ├── claude_desktop_config.example.json   # Claude Desktop 配置示例
│   ├── env.example              # 环境变量示例
│   └── service-account.json     # GCP服务账号
│
├── docs/                        # 📚 文档
│   ├── MCP_DESIGN.md            # MCP 架构设计
│   ├── MCP_DEPLOYMENT.md        # MCP 部署指南
│   ├── MCP_INTEGRATION.md       # MCP 集成指南
│   ├── DEPLOYMENT.md            # 云部署指南
│   ├── SERVICE_LAYER.md         # 服务层文档
│   ├── STORAGE.md               # 存储文档
│   └── ...
│
├── examples/
│   └── mcp_client_example.py    # MCP 客户端示例
│
├── tests/                       # 🧪 测试
│   ├── sample_raw.csv           # 样例原始数据
│   ├── sample_aliases.csv       # 样例别名数据
│   └── test_cleaning.py         # 单元测试
│
├── logs/                        # 📊 日志和输出
│   ├── clean_preview.csv        # 清洗预览 (CSV)
│   ├── clean_preview.json       # 清洗预览 (JSON)
│   ├── service_layer/           # 服务层数据
│   └── validation_report_*.txt  # 校验报告
│
├── ARCHITECTURE.md              # 🏗️ 系统架构设计（新！）
├── CHANGELOG.md                 # 📝 版本历史
├── README.md                    # 本文档
├── QUICKSTART_MCP.md            # MCP 快速开始
├── ministry-data.mcpb           # MCPB 打包文件
├── requirements.txt             # Python 依赖
└── .gitignore                   # Git 忽略文件
```

**架构说明**：
- 🔵 **api/** - 独立的API服务，拥有自己的Dockerfile
- 🟢 **mcp/** - 独立的MCP服务，拥有自己的Dockerfile
- 🔧 **core/** - 共享业务逻辑，被两个服务复用（80%+代码重用）
- 📦 **deploy/** - 独立部署脚本，支持分别或统一部署

## 🔧 技术亮点

- ✅ **标准协议**：符合 MCP 规范，兼容 Claude Desktop 和 ChatGPT
- ✅ **模块化设计**：Tools、Resources、Prompts 独立设计
- ✅ **双传输模式**：支持 stdio（本地）和 HTTP/SSE（云端）
- ✅ **智能清洗**：日期标准化、别名映射、数据校验
- ✅ **云原生**：容器化部署，自动扩展
- ✅ **成本友好**：Cloud Run 免费额度内（~$1/月）

👉 **详细架构**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | [MCP设计](docs/MCP_DESIGN.md)

---

## 📄 验收标准

运行完成后，控制台会打印摘要：

```
============================================================
数据校验报告
============================================================
总行数: 100
成功行数: 95
警告行数: 3
错误行数: 2
总问题数: 5

错误 (2 条):
  行 15 | service_date: 日期格式不正确，应为 YYYY-MM-DD
    值: invalid-date
  行 42 | service_date: 必填字段 'service_date' 不能为空

警告 (3 条):
  行 20 | service_date: 重复的服务记录（日期: 2025-10-05, 时段: morning）
  ...
============================================================

✅ 读取原始表成功：100 行
✅ 清洗成功行：95 行
⚠️  警告行：3 行
❌ 错误行：2 行
✅ 目标表写入成功：95 行（若非 dry-run）
✅ 生成日志文件：logs/validation_report_20251006_100000.txt
```

**退出码**：
- `0`：成功（无错误）
- `1`：有致命错误

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📜 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。
