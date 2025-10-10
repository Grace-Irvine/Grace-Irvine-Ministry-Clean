# 系统架构设计文档

## 📐 架构概览

本系统采用**单一仓库（Monorepo）** 架构，但通过清晰的目录结构和独立的Dockerfile实现了**API服务**和**MCP服务**的职责分离。两个服务共享核心业务逻辑，可以独立部署到Google Cloud Run。

```
┌─────────────────────────────────────────────────────────────┐
│                     用户/客户端层                              │
│                                                               │
│  ┌──────────────┐              ┌──────────────────┐         │
│  │  Web/Mobile  │              │  AI 助手         │         │
│  │  应用        │              │  (Claude/ChatGPT)│         │
│  └──────┬───────┘              └────────┬─────────┘         │
└─────────┼──────────────────────────────┼───────────────────┘
          │                              │
          │ REST API                     │ MCP协议
          │                              │
┌─────────▼──────────────────────────────▼───────────────────┐
│                    服务层 (Cloud Run)                        │
│                                                               │
│  ┌──────────────────┐          ┌──────────────────┐         │
│  │   API Service    │          │   MCP Service    │         │
│  │  数据清洗和管理   │          │  AI助手集成      │         │
│  │                  │          │                  │         │
│  │  - REST API      │          │  - Tools         │         │
│  │  - 数据清洗       │          │  - Resources     │         │
│  │  - 服务层生成     │          │  - Prompts       │         │
│  │  - 统计分析       │          │  - stdio/HTTP    │         │
│  └────────┬─────────┘          └────────┬─────────┘         │
└───────────┼──────────────────────────────┼───────────────────┘
            │                              │
            │        共享核心业务逻辑        │
            │                              │
┌───────────▼──────────────────────────────▼───────────────────┐
│                    核心层 (core/)                             │
│                                                               │
│  clean_pipeline.py     清洗管线                              │
│  service_layer.py      服务层转换器                          │
│  gsheet_utils.py       Google Sheets工具                     │
│  cleaning_rules.py     清洗规则                              │
│  validators.py         数据校验                              │
│  alias_utils.py        别名映射                              │
│  cloud_storage_utils.py Cloud Storage工具                    │
│  change_detector.py    变化检测                              │
└───────────┬───────────────────────────────────────────────────┘
            │
            │ 数据存储访问
            │
┌───────────▼───────────────────────────────────────────────────┐
│                    数据层                                      │
│                                                               │
│  ┌─────────────┬──────────────┬───────────────────────┐     │
│  │ Google      │  Cloud       │  Local Files          │     │
│  │ Sheets      │  Storage     │  (logs/, cache/)      │     │
│  │             │              │                       │     │
│  │ - 原始数据   │ - 服务层数据  │ - 清洗预览            │     │
│  │ - 别名表     │ - 按年份组织  │ - 验证报告            │     │
│  │ - 元数据     │ - JSON格式   │ - 临时缓存            │     │
│  └─────────────┴──────────────┴───────────────────────┘     │
└───────────────────────────────────────────────────────────────┘
```

## 📁 目录结构

```
Grace-Irvine-Ministry-Clean/
│
├── api/                          # API服务
│   ├── app.py                    # FastAPI应用
│   ├── Dockerfile                # API专用Dockerfile
│   ├── __init__.py               # Python包标识
│   └── README.md                 # API服务文档
│
├── mcp/                          # MCP服务
│   ├── mcp_server.py             # stdio模式服务器
│   ├── mcp_http_server.py        # HTTP/SSE模式服务器
│   ├── Dockerfile                # MCP专用Dockerfile
│   ├── __init__.py               # Python包标识
│   └── README.md                 # MCP服务文档
│
├── core/                         # 共享核心业务逻辑
│   ├── __init__.py
│   ├── clean_pipeline.py         # 清洗管线
│   ├── service_layer.py          # 服务层转换
│   ├── gsheet_utils.py           # Google Sheets工具
│   ├── cleaning_rules.py         # 清洗规则
│   ├── validators.py             # 数据校验
│   ├── alias_utils.py            # 别名映射
│   ├── cloud_storage_utils.py    # Cloud Storage工具
│   └── change_detector.py        # 变化检测
│
├── deploy/                       # 部署脚本
│   ├── deploy-api.sh             # API服务部署
│   ├── deploy-mcp.sh             # MCP服务部署
│   └── deploy-all.sh             # 统一部署脚本
│
├── config/                       # 配置文件
│   ├── config.json               # 主配置
│   └── service-account.json      # GCP服务账号
│
├── docs/                         # 文档
├── tests/                        # 测试
├── logs/                         # 日志和输出
│
├── README.md                     # 主文档
├── ARCHITECTURE.md               # 本文档
└── requirements.txt              # Python依赖
```

## 🏗️ 服务架构

### 1. API服务 (api/)

**职责**: 数据清洗、服务层生成、RESTful API访问

#### 核心功能
- 从Google Sheets读取原始数据
- 应用清洗规则（日期标准化、文本清理、别名映射）
- 生成服务层数据（sermon和volunteer领域模型）
- 提供REST API查询清洗后的数据
- 支持统计分析和排班查询

#### 技术栈
- FastAPI - Web框架
- Uvicorn - ASGI服务器  
- Pandas - 数据处理
- Google Sheets API - 数据源

#### 部署
- 独立Dockerfile: `api/Dockerfile`
- Cloud Run服务名: `ministry-data-api`
- 端口: 8080
- 资源: 1GB内存, 1 CPU

### 2. MCP服务 (mcp/)

**职责**: AI助手集成，提供MCP协议接口

#### 核心功能
- 实现MCP协议（Tools、Resources、Prompts）
- 提供stdio模式（本地Claude Desktop）
- 提供HTTP/SSE模式（远程访问）
- 复用core/的业务逻辑执行操作
- 格式化输出适合AI理解的数据

#### 技术栈
- mcp SDK - MCP协议实现
- FastAPI - HTTP/SSE服务器
- AsyncIO - 异步处理

#### 部署
- 独立Dockerfile: `mcp/Dockerfile`
- Cloud Run服务名: `ministry-data-mcp`
- 端口: 8080
- 资源: 512MB内存, 1 CPU

### 3. 核心层 (core/)

**职责**: 共享业务逻辑，被两个服务复用

#### 模块说明

| 模块 | 功能 | 使用方 |
|------|------|--------|
| `clean_pipeline.py` | 清洗管线主流程 | API, MCP |
| `service_layer.py` | 领域模型转换 | API, MCP |
| `gsheet_utils.py` | Google Sheets读写 | API, MCP |
| `cleaning_rules.py` | 清洗规则实现 | clean_pipeline |
| `validators.py` | 数据校验 | clean_pipeline |
| `alias_utils.py` | 别名映射 | cleaning_rules |
| `cloud_storage_utils.py` | Cloud Storage操作 | service_layer |
| `change_detector.py` | 变化检测 | clean_pipeline |

#### 设计原则
- **高内聚**: 每个模块职责单一明确
- **低耦合**: 模块间依赖最小化
- **可测试**: 所有模块都有单元测试
- **可复用**: 被多个服务共享使用

## 🔄 数据流

### 清洗流程
```
1. Google Sheets (原始数据)
   ↓
2. core/clean_pipeline.py (读取)
   ↓
3. core/cleaning_rules.py (清洗)
   ├── 日期标准化
   ├── 文本清理
   ├── 别名映射 (core/alias_utils.py)
   └── 列合并
   ↓
4. core/validators.py (校验)
   ├── 必填字段检查
   ├── 格式验证
   └── 重复检测
   ↓
5. 输出
   ├── logs/clean_preview.json (本地预览)
   ├── logs/clean_preview.csv (CSV格式)
   └── Google Sheets (清洗层)
```

### 服务层生成流程
```
1. 清洗层数据 (logs/clean_preview.json)
   ↓
2. core/service_layer.py
   ├── Sermon Domain转换
   │   ├── 证道信息提取
   │   ├── 讲员信息
   │   └── 诗歌列表
   │
   └── Volunteer Domain转换
       ├── 敬拜团队
       ├── 技术团队
       └── 其他岗位
   ↓
3. 按年份组织
   ├── logs/service_layer/sermon.json (latest)
   ├── logs/service_layer/volunteer.json (latest)
   ├── logs/service_layer/2024/sermon_2024.json
   ├── logs/service_layer/2025/sermon_2025.json
   └── ...
   ↓
4. Cloud Storage (可选)
   └── gs://bucket/domains/sermon/
       ├── sermon_latest.json
       └── 2024/sermon_2024.json
```

### API服务数据流
```
HTTP Request
   ↓
api/app.py (FastAPI端点)
   ↓
core/* (业务逻辑)
   ↓
数据层 (Sheets/Storage/Logs)
   ↓
JSON Response
```

### MCP服务数据流
```
AI助手
   ↓ (MCP协议)
mcp/mcp_http_server.py
   ↓
mcp/mcp_server.py (处理器)
   ↓
core/* (业务逻辑)
   ↓
数据层
   ↓
MCP Response (格式化)
   ↓
AI助手
```

## 🚀 部署架构

### Cloud Run部署

```
┌─────────────────────────────────────┐
│         Google Cloud Run            │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  ministry-data-api           │  │
│  │  - Image: gcr.io/.../api     │  │
│  │  - Port: 8080                │  │
│  │  - Memory: 1GB               │  │
│  │  - CPU: 1                    │  │
│  │  - Max Instances: 3          │  │
│  │  - Source: api/Dockerfile    │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  ministry-data-mcp           │  │
│  │  - Image: gcr.io/.../mcp     │  │
│  │  - Port: 8080                │  │
│  │  - Memory: 512MB             │  │
│  │  - CPU: 1                    │  │
│  │  - Max Instances: 10         │  │
│  │  - Source: mcp/Dockerfile    │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 独立部署优势
- ✅ **资源隔离**: 各自独立的内存和CPU配额
- ✅ **独立扩展**: 根据负载独立自动扩展
- ✅ **独立更新**: 更新一个服务不影响另一个
- ✅ **成本优化**: API服务更多资源，MCP服务更轻量
- ✅ **故障隔离**: 一个服务故障不影响另一个

## 🔐 安全架构

### API服务
- **Cloud Scheduler认证**: Bearer Token保护定时端点
- **服务账号**: 最小权限访问Google Sheets
- **公开端点**: `/health`, `/docs` 等只读端点
- **保护端点**: `/trigger-cleaning` 需要认证

### MCP服务
- **Bearer Token**: 所有MCP端点需要认证
- **Secret Manager**: Token存储在GCP Secrets
- **CORS配置**: 限制跨域访问
- **服务账号**: 只读访问数据源

### 配置文件
- ❌ 不提交 `service-account.json` 到仓库
- ✅ 使用 `.gitignore` 排除敏感文件
- ✅ 生产环境使用Secret Manager
- ✅ 环境变量传递配置

## 📊 监控和日志

### Cloud Logging
```bash
# API服务日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-api"

# MCP服务日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-mcp"
```

### 健康检查
- API: `GET /health`
- MCP: `GET /health`
- 返回状态、时间戳、版本信息

### 指标
- 请求数量和延迟
- 错误率
- 实例数量
- 内存和CPU使用率

## 🧪 测试策略

### 单元测试
- 位置: `tests/test_cleaning.py`
- 覆盖: core/模块的业务逻辑
- 运行: `pytest tests/`

### 集成测试
- API端点测试
- MCP工具测试
- 端到端数据流测试

### 本地测试
```bash
# API服务
python api/app.py

# MCP服务 (stdio)
python mcp/mcp_server.py

# MCP服务 (HTTP)
python mcp/mcp_http_server.py
```

## 🎯 设计决策

### 为什么选择Monorepo？

✅ **代码重用**: 80%+的核心逻辑共享
✅ **统一依赖**: 单一requirements.txt管理
✅ **版本同步**: 不会出现API和MCP版本不一致
✅ **简化维护**: 一个仓库，一套CI/CD
✅ **原子更新**: 核心逻辑变更同步到两个服务

### 为什么独立Dockerfile？

✅ **职责清晰**: 每个服务有明确的构建配置
✅ **优化镜像**: 只包含必要的文件
✅ **独立部署**: 互不干扰
✅ **易于理解**: 新开发者快速上手

### 为什么共享core/?

✅ **避免重复**: DRY原则
✅ **一致性**: 清洗逻辑完全一致
✅ **可维护**: 修复一次，两处受益
✅ **测试效率**: 只需测试一次核心逻辑

## 📚 相关文档

- [主README](README.md) - 项目概述和快速开始
- [API服务文档](api/README.md) - API详细说明
- [MCP服务文档](mcp/README.md) - MCP详细说明
- [部署指南](docs/DEPLOYMENT.md) - 云部署完整指南
- [MCP设计](docs/MCP_DESIGN.md) - MCP架构详细设计

