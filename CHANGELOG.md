# 更新日志

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [2.0.0] - 2025-10-07

### 新增 ✨

#### 服务层（Service Layer）
- 📦 **服务层架构**：将清洗层数据转换为两个独立的领域模型
  - Sermon Domain（证道域）：证道相关的核心信息
  - Volunteer Domain（同工域）：主日服侍同工信息
- 🔄 **自动生成所有年份**：智能检测并生成所有历史年份的数据
- ☁️ **Cloud Storage 集成**：自动上传到 Google Cloud Storage
- 📊 **数据组织**：按领域和年份组织文件（latest + yearly）

#### 云部署（Cloud Deployment）
- ☁️ **Cloud Run 部署**：一键部署到 Google Cloud Run
- ⏰ **Cloud Scheduler**：定时任务自动更新数据（每30分钟）
- 🔍 **智能变化检测**：SHA-256哈希比对，仅在数据变化时执行清洗
- 🚀 **FastAPI 应用**：提供完整的 RESTful API
- 🔒 **Bearer Token 认证**：保护定时触发端点

#### API 端点
- `POST /api/v1/clean` - 手动触发数据清洗
- `POST /api/v1/query` - 查询数据（支持多种过滤条件）
- `GET /api/v1/stats` - 获取统计信息
- `GET /api/v1/preview` - 获取最新清洗预览
- `POST /api/v1/service-layer/generate` - 生成服务层数据
- `GET /api/v1/sermon` - 获取证道域数据
- `GET /api/v1/volunteer` - 获取同工域数据
- `POST /trigger-cleaning` - Cloud Scheduler 触发端点
- `GET /mcp/tools` - MCP 工具定义

#### 存储和数据管理
- 📦 **Google Cloud Storage Bucket**：grace-irvine-ministry-data
- 📁 **文件组织结构**：domains/sermon|volunteer/{latest, 2024, 2025, 2026}
- 🔄 **版本控制**：支持历史版本管理

#### 工具和脚本
- `scripts/service_layer.py` - 服务层转换器
- `scripts/cloud_storage_utils.py` - 云存储工具
- `scripts/change_detector.py` - 变化检测
- `app.py` - FastAPI 应用
- `Dockerfile` - 容器配置
- `deploy-cloud-run.sh` - 部署脚本
- `setup-cloud-scheduler.sh` - 定时任务设置

#### 测试脚本
- `test_deployed_api.sh` - API 端点测试
- `test_change_detection.sh` - 变化检测测试
- `test_service_layer.sh` - 服务层测试
- `test_all_years_api.sh` - 所有年份API测试

#### 文档
- `SERVICE_LAYER.md` - 服务层完整文档
- `DEPLOYMENT.md` - 云部署完整文档
- `STORAGE.md` - 存储和数据管理文档
- `MCP_INTEGRATION.md` - MCP 集成指南
- `TROUBLESHOOTING.md` - 故障排除指南
- `QUICK_COMMANDS.md` - 快速命令参考
- `ARCHITECTURE.md` - 项目架构文档

### 改进 🔧

#### 性能优化
- ⚡ **智能跳过**：无数据变化时< 1秒返回
- 🎯 **并行处理**：多年份并行生成
- 📊 **增量更新**：仅更新变化的部分

#### 用户体验
- 📝 **详细日志**：完整的操作记录和错误信息
- 🎨 **交互式 API 文档**：Swagger UI（/docs）
- 📊 **实时统计**：动态数据统计和分析

### 技术栈更新 🛠️

#### 新增依赖
- `fastapi>=0.109.0` - Web 框架
- `uvicorn[standard]>=0.27.0` - ASGI 服务器
- `pydantic>=2.5.0` - 数据验证
- `google-cloud-storage` - GCS 集成（可选）
- `python-multipart>=0.0.6` - 文件上传支持

#### 部署工具
- Docker - 容器化
- Google Cloud Build - 镜像构建
- Google Cloud Run - 无服务器部署
- Google Cloud Scheduler - 定时任务
- Google Cloud Storage - 对象存储

### 数据流 🔄

```
原始层 (Google Sheets)
    ↓
清洗层 (Google Sheets)
    ↓
服务层 (JSON)
    ├── Sermon Domain
    └── Volunteer Domain
    ↓
Cloud Storage (GCS)
    ├── latest.json
    └── yearly files (2024, 2025, 2026)
```

### 成本估算 💰

- **Cloud Run**：~$0.57/月（基本在免费额度内）
- **Cloud Scheduler**：$0.00/月（免费额度内）
- **Cloud Storage**：< $0.01/月（490 KB）
- **总计**：~$0.57/月

### 安全更新 🔒

- 🔐 Bearer Token 认证保护定时任务
- 🔒 Secret Manager 存储敏感凭证
- 🛡️ 最小权限原则（IAM）
- 🔍 详细的审计日志

---

## [1.0.0] - 2025-10-06

### 新增 ✨

#### 核心功能
- 完整的数据清洗管线，支持从原始 Google Sheet 到清洗层 Google Sheet 的自动化清洗
- 可配置的清洗规则（通过 `config/config.json` 管理）
- 人名别名映射功能，支持多对一映射（中文名/英文名/昵称 → 统一 ID）
- 数据校验功能，生成详细的错误和警告报告
- Dry-run 模式，支持先预览后写入

#### 清洗规则
- 日期标准化（支持多种格式输入，统一输出 YYYY-MM-DD）
- 文本清理（去除空格、全角空格、占位符处理）
- 经文引用标准化
- 歌曲拆分与去重（支持多种分隔符）
- 列合并功能（如合并多个敬拜同工列）
- 服务周数自动计算（ISO 周数）

#### 模块
- `gsheet_utils.py`: Google Sheets API 封装
- `cleaning_rules.py`: 清洗规则实现
- `alias_utils.py`: 别名映射工具
- `validators.py`: 数据校验器
- `clean_pipeline.py`: 主清洗管线

#### 工具和脚本
- `run_pipeline.sh`: 便捷执行脚本，支持参数解析和环境检查
- 完整的单元测试套件（`tests/test_cleaning.py`）
- 样例数据（`tests/sample_raw.csv`, `tests/sample_aliases.csv`）

#### 文档
- 完整的用户指南（`README.md`）
- 快速上手指南（`QUICKSTART.md`）
- 项目概览文档（`PROJECT_OVERVIEW.md`）
- 任务说明文档（`README_prompt.md`）
- 示例配置文件（`config/config.example.json`）

#### 输出
- CSV 预览文件
- JSON 预览文件
- 详细的校验报告（保存到 `logs/`）
- 控制台摘要输出

### 安全 🔒
- 最小权限原则（原始表只读、清洗表只写）
- 服务账号认证
- 敏感信息保护（`.gitignore` 配置）
- 日志不打印敏感令牌

### 测试 🧪
- 单元测试覆盖所有核心功能（17个测试，100%通过）
- 日期清洗测试
- 别名映射测试
- 歌曲拆分测试
- 列合并测试
- 数据校验测试
- 完整管线测试

---

## 版本说明

### 版本号格式：主版本号.次版本号.修订号

- **主版本号（Major）**：不兼容的 API 变更
- **次版本号（Minor）**：向下兼容的功能新增
- **修订号（Patch）**：向下兼容的问题修复

### 变更类型

- **新增（Added）**：新功能
- **变更（Changed）**：现有功能的变更
- **废弃（Deprecated）**：即将移除的功能
- **移除（Removed）**：已移除的功能
- **修复（Fixed）**：问题修复
- **安全（Security）**：安全相关的变更
