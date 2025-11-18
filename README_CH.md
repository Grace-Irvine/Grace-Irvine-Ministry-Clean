# 恩典欧文教会主日事工数据管理系统

> **Language / 语言**: [English](README.md) | [中文](README_CH.md)

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118+-green.svg)](https://fastapi.tiangolo.com/)
[![MCP](https://img.shields.io/badge/MCP-1.16+-purple.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个完整的教会主日事工数据管理系统，具备智能数据清洗、领域模型转换、RESTful API，以及**通过模型上下文协议（MCP）的 AI 助手集成**功能。

---

## 目录

- [✨ 概述](#-概述)
- [🏗️ 系统架构](#️-系统架构)
- [🚀 快速开始](#-快速开始)
- [📚 文档导航](#-文档导航)
- [🔑 核心特性](#-核心特性)
- [🛠️ 技术栈](#-技术栈)
- [📦 项目结构](#-项目结构)
- [💡 使用示例](#-使用示例)
- [🧪 测试](#-测试)
- [🤝 贡献](#-贡献)

---

## ✨ 概述

**恩典欧文教会主日事工数据管理系统**是一个生产就绪、AI 原生的应用程序，旨在：

1. **清洗和标准化**来自 Google Sheets 的原始事工数据
2. **转换**扁平数据为结构化领域模型（证道域 + 同工域）
3. **提供**RESTful API 端点用于数据分析和应用程序访问
4. **支持 AI 集成**通过模型上下文协议（MCP）
5. **无缝部署**到 Google Cloud Run，支持自动化调度

### 特色亮点

- **🤖 AI 原生设计**：内置 MCP 服务器，支持 Claude、ChatGPT 等 AI 助手进行自然语言查询
- **🏗️ 清晰架构**：2 层设计（清洗层 + 服务层），80%+ 代码复用
- **☁️ 云原生就绪**：容器化微服务，自动扩展，低成本（约 $1/月）
- **⚡ 智能优化**：变化检测、并行处理、增量更新
- **📦 可打包**：通过 MCPB 包一键安装到 Claude Desktop

---

## 🏗️ 系统架构

### 单一仓库（Monorepo）+ 独立微服务

```text
Grace-Irvine-Ministry-Clean/
├── api/          # API 服务 - 数据清洗和 REST API（FastAPI）
├── mcp/          # MCP 服务 - AI 助手集成（MCP 协议）
├── core/         # 共享业务逻辑（80%+ 代码复用）
├── deploy/       # 部署脚本
└── config/       # 配置文件
```

### 两个独立服务

| 服务               | 用途                         | 技术栈            | 端口 | 部署方式  |
| ------------------ | ---------------------------- | ----------------- | ---- | --------- |
| **API 服务** | 数据清洗、REST API、统计分析 | FastAPI + Uvicorn | 8080 | Cloud Run |
| **MCP 服务** | AI 助手集成、自然语言查询    | MCP SDK + FastAPI | 8080 | Cloud Run |

两个服务可以**独立运行**，同时共享 `core/` 业务逻辑。

### 2 层清晰架构

#### 第 1 层：清洗层

**目的**：标准化来自 Google Sheets 的原始数据

**文件**：[core/clean_pipeline.py](../core/clean_pipeline.py)

**转换操作**：

- 日期标准化（多种格式 → YYYY-MM-DD）
- 文本清理（去除空格、处理占位符）
- 别名映射（多个名字 → 统一的 person_id）- *v4.3.0 优化匹配准确性*
- 歌曲拆分（支持多种分隔符）
- 经文格式化（在书名和章节之间添加空格）
- 列合并（worship_team_1 + worship_team_2 → worship_team 列表）
- **新增部门**：饭食组（Meal Group）和祷告部（Prayer Department）
- 数据验证（必填字段、重复项、格式检查）

**输出**：29 字段标准化架构，写入 Google Sheets "CleanData" 表

#### 第 2 层：服务层

**目的**：将扁平的清洗数据转换为结构化领域模型

**文件**：[core/service_layer.py](../core/service_layer.py)

**领域模型**：

1. **证道域（Sermon Domain）** - 证道元数据及讲员和诗歌信息

   ```json
   {
     "service_date": "2024-01-07",
     "sermon": {
       "title": "福音系列第一部分",
       "series": "遇见耶稣",
       "scripture": "创世记 3"
     },
     "preacher": {"id": "person_6511_wangtong", "name": "王通"},
     "songs": ["奇异恩典", "确据"]
   }
   ```
2. **同工域（Volunteer Domain）** - 按角色分类的同工分配

   ```json
   {
     "service_date": "2024-01-07",
     "worship": {
       "lead": {"id": "person_xiem", "name": "谢苗"},
       "team": [{"id": "person_quixiaohuan", "name": "瞿小欢"}],
       "pianist": {"id": "person_shawn", "name": "Shawn"}
     },
     "technical": {
       "audio": {"id": "person_3850_jingzheng", "name": "景峥"},
       "video": {"id": "person_2012_junxin", "name": "俊鑫"}
     }
   }
   ```

**输出**：按领域和年份组织的 JSON 文件，可选上传到 Google Cloud Storage

### 完整数据流程

```text
原始数据（Google Sheets）
    ↓
清洗管道
    ├── 日期标准化
    ├── 文本清理
    ├── 别名映射
    ├── 歌曲拆分
    └── 数据验证
    ↓
清洗后数据（Google Sheets + 本地 JSON/CSV）
    ↓
服务层转换器
    ├── 证道领域模型
    └── 同工领域模型
    ↓
领域存储
    ├── 本地：logs/service_layer/{domain}_latest.json
    ├── 年度：logs/service_layer/{year}/{domain}_{year}.json
    └── 云端：gs://bucket/domains/{domain}/{files}
    ↓
访问层
    ├── REST API（api/app.py）
    ├── MCP 资源（mcp/mcp_server.py）
    └── AI 助手（Claude、ChatGPT）
```

---

## 🚀 快速开始

### 方式 1：AI 助手集成（推荐）🤖

通过 MCP 协议与 Claude Desktop 或 ChatGPT 集成：

**Claude Desktop（stdio 模式）**：

```bash
# 本地运行 MCP 服务器
python mcp/mcp_server.py
```

**云端部署（HTTP/SSE 模式）**：

```bash
# 部署到 Cloud Run
./deploy/deploy-mcp.sh
```

**功能特性**：

- 自然语言查询
- 预定义分析提示词
- 9 个工具用于数据操作
- 22+ 资源用于数据访问

👉 **详见**：[MCP 服务器文档](../mcp/README.md) | [MCP 架构设计](MCP_DESIGN.md)

---

### 方式 2：本地数据清洗

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置服务账号
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# 3. 编辑配置文件
vim config/config.json

# 4. 使用 dry-run 模式测试
python core/clean_pipeline.py --config config/config.json --dry-run

# 5. 运行清洗管道
python core/clean_pipeline.py --config config/config.json
```

👉 **详见**：快速开始部分

---

### 方式 3：云端部署

将 API 和 MCP 服务部署到 Google Cloud Run：

```bash
# 设置 GCP 项目 ID
export GCP_PROJECT_ID=your-project-id

# 部署所有服务
./deploy/deploy-all.sh
```

**功能特性**：

- 根据流量自动扩展
- 定时更新（每 30 分钟）
- 低成本（免费额度内约 $1/月）
- Bearer Token 认证

👉 **详见**：云端部署部分

---

## 📚 其他资源

- **MCP 服务器指南**: 查看 `mcp/README.md` 了解完整的 MCP 使用指南
- **API 文档**: 本地运行时可通过 `/docs` 端点访问交互式 API 文档
- **部署脚本**: 查看 `deploy/` 目录了解部署自动化脚本

---

## 🔑 核心特性

### 🤖 AI 助手集成（MCP 协议）

**9 个工具**（面向操作）：

- `query_volunteers_by_date` - 查询同工分配
- `query_sermon_by_date` - 查询证道信息
- `query_date_range` - 跨日期范围查询
- `clean_ministry_data` - 触发清洗管道
- `generate_service_layer` - 生成领域模型
- `validate_raw_data` - 验证数据质量
- `sync_from_gcs` - 从云存储同步
- `check_upcoming_completeness` - 检查未来排期
- `generate_weekly_preview` - 生成每周预览

**22+ 资源**（只读数据访问）：

- `ministry://sermon/records/{year}` - 证道记录
- `ministry://sermon/by-preacher/{name}` - 按讲员查询证道
- `ministry://volunteer/assignments/{date}` - 同工分配
- `ministry://volunteer/by-person/{id}` - 服事历史
- `ministry://stats/summary` - 总体统计

**12+ 提示词**（预定义分析模板）：

- `analyze_preaching_schedule` - 分析证道模式
- `analyze_volunteer_balance` - 检查服事负载平衡
- `find_scheduling_gaps` - 查找未填补的岗位
- `suggest_preacher_rotation` - 建议讲员排期
- `check_data_quality` - 数据质量评估

**双传输模式**：

- **stdio**：用于 Claude Desktop 本地集成（无网络开销）
- **HTTP/SSE**：用于远程客户端的云集成

---

### 📊 数据管理

**智能清洗**：

- 日期标准化（多种格式 → YYYY-MM-DD）
- 文本清理（空格、占位符、标准化）
- 别名映射（多个名字 → 统一的 person_id）
- 歌曲拆分和去重
- 经文格式化
- 列合并
- 全面验证

**服务层转换**：

- 证道领域模型（证道、讲员、诗歌）
- 同工领域模型（角色、分配、可用性）
- 按年份分区（2024-2026+）
- 云存储备份（Google Cloud Storage）

**变化检测**：

- SHA-256 哈希比较
- 无变化时跳过处理
- 重复运行快 99%+
- 减少 API 调用和成本

---

### ☁️ 云端部署

**API 服务**：

- 完整的 REST API 用于数据访问
- 数据清洗端点
- 统计和分析
- Bearer Token 认证
- 自动扩展（1GB 内存，最多 3 个实例）

**MCP 服务**：

- HTTP/SSE 端点用于 MCP 协议
- 远程 AI 助手集成
- Bearer Token 认证
- 自动扩展（512MB 内存，最多 10 个实例）

**调度**：

- Cloud Scheduler 每 30 分钟触发一次
- 变化检测防止不必要的运行
- 自动化数据更新

**成本优化**：

- 在 Google Cloud 免费额度内（约 $1/月）
- 按使用量付费
- 智能缓存和优化

---

## 🛠️ 技术栈

### 后端框架

| 组件                  | 技术          | 版本   | 用途           |
| --------------------- | ------------- | ------ | -------------- |
| **API 框架**    | FastAPI       | 0.118+ | 异步 HTTP 端点 |
| **ASGI 服务器** | Uvicorn       | 0.37+  | 生产服务器     |
| **MCP SDK**     | mcp (Python)  | 1.16+  | 模型上下文协议 |
| **SSE 传输**    | sse-starlette | 2.0+   | 服务器发送事件 |
| **数据处理**    | Pandas        | 2.2+   | DataFrame 操作 |
| **类型验证**    | Pydantic      | 2.12+  | 数据模型       |

### Google Cloud 集成

| 组件                        | 技术                            | 用途             |
| --------------------------- | ------------------------------- | ---------------- |
| **Google Sheets API** | google-api-python-client 2.149+ | 读写数据         |
| **Cloud Storage**     | google-cloud-storage 2.10+      | 文件存储         |
| **身份认证**          | google-auth 2.34+               | OAuth2、服务账号 |

### 基础设施与部署

| 组件               | 技术             | 用途         |
| ------------------ | ---------------- | ------------ |
| **容器化**   | Docker           | 容器镜像     |
| **云托管**   | Google Cloud Run | 无服务器计算 |
| **调度**     | Cloud Scheduler  | 定期更新     |
| **密钥管理** | Secret Manager   | 令牌存储（✅ 已集成） |
| **日志**     | Cloud Logging    | 集中式日志   |

---

## 📦 项目结构

```text
Grace-Irvine-Ministry-Clean/
│
├── api/                         # 🔵 API 服务（数据清洗和 REST API）
│   ├── app.py                   # FastAPI 应用程序
│   ├── Dockerfile               # API 服务容器
│   └── README.md                # API 文档
│
├── mcp/                         # 🟢 MCP 服务（AI 助手集成）
│   ├── mcp_server.py            # 统一 MCP 服务器（stdio + HTTP）
│   ├── sse_transport.py         # HTTP/SSE 传输处理器
│   ├── Dockerfile               # MCP 服务容器
│   └── README.md                # MCP 文档
│
├── core/                        # 🔧 共享业务逻辑（80%+ 复用）
│   ├── clean_pipeline.py        # 主清洗编排
│   ├── service_layer.py         # 服务层转换器
│   ├── cleaning_rules.py        # 清洗规则
│   ├── validators.py            # 数据验证器
│   ├── alias_utils.py           # 别名映射
│   ├── gsheet_utils.py          # Google Sheets 客户端
│   ├── cloud_storage_utils.py   # Cloud Storage 客户端
│   ├── change_detector.py       # 变化检测
│   ├── schema_manager.py        # Schema 管理
│   └── secret_manager_utils.py  # Secret Manager 工具
│
├── deploy/                      # 📦 部署脚本
│   ├── deploy-api.sh            # 部署 API 服务
│   ├── deploy-mcp.sh            # 部署 MCP 服务
│   └── deploy-all.sh            # 部署所有服务
│
├── config/                      # ⚙️ 配置文件
│   ├── config.json              # 主配置
│   ├── claude_desktop_config.example.json   # Claude Desktop 配置
│   ├── env.example              # 环境变量
│   └── service-account.json     # GCP 服务账号
│
├── tests/                       # 🧪 测试
│   ├── test_cleaning.py         # 单元测试
│   ├── sample_raw.csv           # 样本原始数据
│   └── sample_aliases.csv       # 样本别名
│
├── logs/                        # 📊 日志和输出
│   ├── clean_preview.csv        # 清洗后数据（CSV）
│   ├── clean_preview.json       # 清洗后数据（JSON）
│   ├── service_layer/           # 服务层数据
│   └── validation_report_*.txt # 验证报告
│
├── CHANGELOG.md                 # 版本历史
├── README.md                    # 英文自述文件
├── README_CH.md                 # 中文自述文件（本文件）
├── requirements.txt             # Python 依赖
└── .gitignore                   # Git 忽略规则
```

---

## 💡 使用示例

### 示例 1：通过 Claude Desktop 进行 AI 查询

**用户**："显示下周日的服事安排"

**Claude**（使用 MCP 工具）：

```text
使用 query_volunteers_by_date 工具，日期=2025-10-26...

下周日（2025-10-26）服事安排：

📖 证道："祷告的力量" - 张牧师
   系列：祷告系列 | 经文：马太福音 6:9-13

🎵 敬拜团队：
   - 带领：王丽
   - 团队：陈明、林芳
   - 司琴：李伟

🎤 技术团队：
   - 音控：赵强
   - 导播：周晨
```

---

### 示例 2：REST API 查询

```bash
# 获取 2024 年的证道记录
curl "https://your-api.run.app/api/v1/sermon?year=2024"

# 获取特定人员的同工分配
curl "https://your-api.run.app/api/v1/volunteer/by-person/person_wangli"

# 触发数据清洗（需要 Bearer token）
curl -X POST "https://your-api.run.app/api/v1/clean" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

---

### 示例 3：本地清洗管道

```bash
# 使用 dry-run 模式测试
python core/clean_pipeline.py --config config/config.json --dry-run

# 输出：
# ✅ 读取源数据：100 行
# ✅ 清洗成功：95 行
# ⚠️  警告：3 行
# ❌ 错误：2 行
# ✅ 生成 logs/clean_preview.json

# 运行实际清洗
python core/clean_pipeline.py --config config/config.json
```

---

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

### 测试覆盖范围

单元测试涵盖：

- ✅ 日期格式清洗和标准化
- ✅ 文本清理（空格、占位符）
- ✅ 经文引用格式化
- ✅ 歌曲拆分和去重
- ✅ 列合并
- ✅ 别名映射
- ✅ 数据验证（必填字段、日期有效性、重复检测）

### 样本数据

`tests/sample_raw.csv` 包含各种测试场景：

- 不同的日期格式
- 带空格的文本
- 多种歌曲分隔符
- 别名
- 空值和占位符
- 无效日期（用于错误处理测试）

---

## 🔒 安全与权限

### 最小权限原则

- ✅ 源表：只读（Viewer）权限
- ✅ 目标表：仅写入特定范围
- ✅ 别名表：只读（Viewer）权限

### 敏感信息保护

- ❌ **禁止**将服务账号 JSON 文件提交到代码仓库
- ✅ 使用 `.gitignore` 排除 `*.json`（除了 `config/config.json`）
- ✅ 使用环境变量 `GOOGLE_APPLICATION_CREDENTIALS`
- ✅ **Secret Manager 集成**：所有服务自动从 Google Secret Manager 读取 tokens
- ✅ **自动降级机制**：服务优先从 Secret Manager 读取，然后使用环境变量
- ✅ 生产环境使用 Secret Manager 存储令牌（推荐）
- ✅ 本地开发使用环境变量
- ❌ 日志中不打印敏感令牌

**Secret Manager 支持**：
- 所有 3 个 Cloud Run 服务已集成 Secret Manager
- 管理的 4 个 secrets：`mcp-bearer-token`、`api-scheduler-token`、`weekly-preview-scheduler-token`、`weekly-preview-smtp-password`
- 支持自动 token 轮换

### 身份认证

**API 服务**：

- 受保护端点使用 Bearer Token 认证
- 健康检查和文档公开访问
- 通过环境变量配置

**MCP 服务**：

- HTTP/SSE 模式使用 Bearer Token 认证（可选）
- stdio 模式无需认证（仅本地）
- 为远程客户端启用 CORS 中间件
- Bearer Token 自动从 Secret Manager 读取（`mcp-bearer-token`）

---

## 🤝 贡献

我们欢迎贡献！以下是您可以提供帮助的方式：

1. **报告问题**：发现 bug？[提交 issue](https://github.com/yourusername/Grace-Irvine-Ministry-Clean/issues)
2. **建议功能**：有想法？在讨论中分享
3. **提交 PR**：Fork 项目，创建功能分支，提交 pull request
4. **改进文档**：帮助我们使文档更清晰

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/Grace-Irvine-Ministry-Clean.git
cd Grace-Irvine-Ministry-Clean

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/ -v

# 本地启动 API 服务
cd api && uvicorn app:app --reload

# 本地启动 MCP 服务
cd mcp && python mcp_server.py
```

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](../LICENSE) 文件。

---

## 🙏 致谢

- **FastAPI** - 现代 Python Web 框架
- **MCP SDK** - 模型上下文协议实现
- **Google Cloud** - 云基础设施
- **Anthropic Claude** - AI 助手集成

---

## 📞 支持

- **问题反馈**：[GitHub Issues](https://github.com/yourusername/Grace-Irvine-Ministry-Clean/issues)
- **邮箱**：jonathanjing@graceirvine.org

---

**用 ❤️ 为恩典欧文教会主日事工打造**

