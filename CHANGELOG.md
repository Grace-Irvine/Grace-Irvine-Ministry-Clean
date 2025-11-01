# 更新日志

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [4.0.3] - 2025-01-XX

### 🔐 安全增强：Google Secret Manager 集成

**完整集成 Secret Manager 用于管理所有动态 tokens 和敏感信息**

#### 新增功能 ✨

##### 1. Secret Manager 工具模块
- ✅ 新增 `core/secret_manager_utils.py` - Secret Manager 辅助工具
  - `SecretManagerHelper` 类：封装 Secret Manager 客户端
  - `get_secret_from_manager()`: 获取 secret 值
  - `get_token_from_manager()`: 获取 token（便捷方法）
  - 自动缓存机制（5分钟缓存，减少 API 调用）
  - 优雅降级支持（Secret Manager 不可用时使用环境变量）

##### 2. 服务集成 Secret Manager

**所有 3 个 Cloud Run 服务已集成 Secret Manager：**

- ✅ **ministry-data-mcp** (MCP Server)
  - 自动从 Secret Manager 读取 `mcp-bearer-token`
  - 代码位置: `mcp/mcp_server.py`

- ✅ **ministry-data-cleaning** (API Service)
  - 自动从 Secret Manager 读取 `api-scheduler-token`
  - 代码位置: `api/app.py`

- ✅ **weekly-preview-scheduler** (Weekly Preview Service)
  - 自动从 Secret Manager 读取：
    - `mcp-bearer-token` (调用 MCP Server)
    - `weekly-preview-scheduler-token` (Scheduler 认证)
    - `weekly-preview-smtp-password` (邮件发送)
  - 代码位置: `mcp/example/weekly_preview_scheduler.py`

##### 3. 自动读取机制

所有服务实现统一的读取优先级：
1. **环境变量**（优先）- 用于本地开发
2. **Secret Manager**（自动）- 生产环境自动读取
3. **默认值**（降级）- 某些服务有默认值

##### 4. 文档完善

- ✅ 新增 `docs/SECRET_MANAGEMENT.md` - Secret Manager 最佳实践指南
- ✅ 新增 `docs/SECRETS_INVENTORY.md` - 完整的 Secrets 清单和操作指南
- ✅ 更新所有配置文件（`config/env.example`, `mcp/example/config.env.example`, `mcp/example/secrets.env.example`）
- ✅ 更新服务文档（`api/README.md`）
- ✅ 更新主 README 文档（Secret Manager 集成说明）

#### Secrets 清单 🔐

| Secret 名称 | 使用服务 | 类型 | 用途 |
|------------|---------|------|------|
| `mcp-bearer-token` | ministry-data-mcp, weekly-preview-scheduler | Token | MCP 服务认证 |
| `api-scheduler-token` | ministry-data-cleaning | Token | API 调度器认证 |
| `weekly-preview-scheduler-token` | weekly-preview-scheduler | Token | 预览服务调度器认证 |
| `weekly-preview-smtp-password` | weekly-preview-scheduler | Password | 邮件发送密码 |

#### 技术实现 🛠️

- ✅ 添加 `google-cloud-secret-manager>=2.20.0` 依赖
- ✅ 实现自动降级机制（Secret Manager → 环境变量 → 默认值）
- ✅ 实现缓存机制（5分钟 TTL，减少 API 调用）
- ✅ 完整的错误处理和日志记录

#### 配置文件更新 📝

所有配置文件已更新，包含：
- Secret Manager 使用说明
- 自动读取机制说明
- 本地开发 vs 生产环境的推荐方案
- 文档引用链接

**更新的配置文件**:
- `config/env.example` - MCP Server 配置
- `mcp/example/config.env.example` - Weekly Preview 服务配置
- `mcp/example/secrets.env.example` - 敏感信息配置

#### 优势 🌟

- ✅ **安全性**: 加密存储，访问控制
- ✅ **可管理性**: 版本管理，审计日志
- ✅ **易用性**: 自动读取，无需手动配置
- ✅ **可扩展性**: 支持多个 secrets，自动轮换
- ✅ **成本效益**: 按使用量计费，价格合理

#### 参考文档 📚

- [Secret Management Best Practices](docs/SECRET_MANAGEMENT.md) - 最佳实践指南
- [Secrets Inventory](docs/SECRETS_INVENTORY.md) - 完整的 Secrets 清单

---

## [4.0.2] - 2025-10-22

### 🐛 主要修复：GCS 数据读取问题

**从"空数据响应"到"成功读取 210 条记录"**

#### 1. 核心问题诊断 ✅

##### 问题表现
- MCP 工具成功连接 GCS bucket
- 文件下载成功，但返回 `total_records: 0`
- 响应时间正常（100-300ms），非超时问题
- 数据源显示为 `gcs`，但实际无有效数据

##### 根本原因
- **数据结构不匹配**：`_sync_latest_from_yearly` 方法从年度文件读取 `'records'` 字段，但年度文件实际使用 `'volunteers'` 和 `'sermons'` 字段
- **路径处理错误**：`list_files` 返回包含 `base_path` 的完整路径，但 `download_json` 又会添加 `base_path`，导致路径重复（`domains/domains/...`）

#### 2. 代码修复 ✅

##### [core/cloud_storage_utils.py:336-367](core/cloud_storage_utils.py#L336-L367) - 数据结构修复
```python
# 修复前：尝试读取不存在的字段
if 'records' in year_data:
    all_records.extend(year_data['records'])

merged_data = {
    'records': all_records  # 错误：MCP server 期望 'volunteers' 或 'sermons'
}

# 修复后：使用正确的字段名
record_field_name = f"{domain_name}s" if domain_name == "volunteer" else "sermons"
records = (year_data.get(record_field_name) or
          year_data.get('records') or
          year_data.get(domain_name + 's') or [])

merged_data = {
    record_field_name: all_records  # 正确：'volunteers' 或 'sermons'
}
```

##### [core/cloud_storage_utils.py:340-342](core/cloud_storage_utils.py#L340-L342) - 路径处理修复
```python
# 修复前：路径重复问题
year_data = self.gcs_client.download_json(file_path)  # file_path 包含 base_path

# 修复后：移除 base_path 前缀
relative_path = file_path.replace(self.gcs_client.base_path, '', 1)
year_data = self.gcs_client.download_json(relative_path)
```

#### 3. GCS 数据重新生成 ✅

##### 执行同步脚本
```bash
python3 -c "from core.cloud_storage_utils import DomainStorageManager; ..."
```

##### 结果验证
- ✅ `volunteer/latest.json`: 210 条记录（263.39 KiB）
- ✅ `sermon/latest.json`: 210 条记录（98.8 KiB）
- ✅ 日期范围：2024-01-07 到 2026-07-05
- ✅ 数据结构：使用 `volunteers` 和 `sermons` 字段

#### 4. MCP 服务器诊断增强 ✅

##### [mcp/mcp_server.py:1410-1555](mcp/mcp_server.py#L1410-L1555) - 增强诊断工具

**新增 `diagnose_gcs_connection` 功能**：
- ✅ 检查 GCS 客户端初始化状态
- ✅ 测试 GCS 连接并列出文件
- ✅ 验证数据内容（记录数量、日期范围）
- ✅ 对比 GCS 和本地数据源
- ✅ 提供详细的故障排查建议

**诊断报告示例**：
```
🔍 GCS 连接诊断报告

✅ GCS 客户端: 已初始化
✅ GCS 连接测试: 成功 (找到 4 个文件)

📊 数据源对比:
  VOLUNTEER:
    GCS: 210 条记录 (2024-01-07 to 2026-07-05)
    本地: 210 条记录 (2024-01-07 to 2026-07-05)
  SERMON:
    GCS: 210 条记录 (2024-01-07 to 2026-07-05)
    本地: 210 条记录 (2024-01-07 to 2026-07-05)

💡 建议:
  ✅ GCS 连接正常，数据可正常读取
```

---

## [4.0.1] - 2025-10-20

### 🎉 重大更新：服务层架构与 GCS 集成

**从"Google Sheets 清洗"升级到"完整的数据服务系统"**

#### 核心功能 ✨

##### 1. 服务层架构（Service Layer）

**新增 `core/service_layer.py`**：
- ✅ 2 个领域模型：Sermon Domain、Volunteer Domain
- ✅ 扁平数据转换为结构化 JSON
- ✅ 支持增量更新和版本控制
- ✅ 本地存储和 GCS 上传

**领域模型**：
- **Sermon Domain**: 讲道元数据（讲员、经文、系列、诗歌）
- **Volunteer Domain**: 事工人员分配（日期、部门、角色、人员）

##### 2. Google Cloud Storage 集成

**新增 `core/cloud_storage_utils.py`**：
- ✅ GCS 客户端封装
- ✅ 文件上传/下载
- ✅ 年度文件管理（2024.json, 2025.json, ...）
- ✅ 最新文件同步（latest.json）
- ✅ 文件列表和版本管理

**存储结构**：
```
grace-irvine-ministry-data/
└── domains/
    ├── sermon/
    │   ├── latest.json
    │   ├── 2024.json
    │   ├── 2025.json
    │   └── 2026.json
    └── volunteer/
        ├── latest.json
        ├── 2024.json
        ├── 2025.json
        └── 2026.json
```

##### 3. MCP 服务器增强

**新增资源（Resources）**：
- ✅ `ministry://sermon/records` - 讲道记录列表
- ✅ `ministry://volunteer/records` - 事工人员记录列表
- ✅ `ministry://sermon/latest` - 最新讲道记录
- ✅ `ministry://volunteer/latest` - 最新事工记录
- ✅ `ministry://sermon/{date}` - 按日期查询讲道
- ✅ `ministry://volunteer/{date}` - 按日期查询事工
- ✅ `ministry://sermon/range?start={start}&end={end}` - 日期范围查询
- ✅ `ministry://volunteer/range?start={start}&end={end}` - 日期范围查询

**新增工具（Tools）**：
- ✅ `generate_service_layer` - 生成服务层数据
- ✅ `sync_from_gcs` - 从 GCS 同步数据
- ✅ `check_upcoming_completeness` - 检查未来安排完整性

#### 数据流架构 🏗️

```
原始数据 (Google Sheets)
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
