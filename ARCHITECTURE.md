# 项目概览

## 📚 文档索引

| 文档 | 用途 | 受众 |
|-----|------|------|
| [README.md](README.md) | 完整用户指南和 API 文档 | 所有用户 |
| [QUICKSTART.md](QUICKSTART.md) | 5 分钟快速上手指南 | 新用户 |
| [prompts/README_prompt.md](prompts/README_prompt.md) | 详细任务说明和设计规范 | 开发者 |
| PROJECT_OVERVIEW.md（本文档） | 项目结构和模块说明 | 开发者 |

## 🏗️ 项目架构

```
church-ministry-clean/
│
├── 📁 config/              配置文件目录
│   └── config.json        主配置文件（包含 Sheet URL、列映射、清洗规则等）
│
├── 📁 scripts/             核心脚本模块
│   ├── __init__.py        模块初始化
│   ├── clean_pipeline.py  ⭐ 主清洗管线（入口点）
│   ├── gsheet_utils.py    Google Sheets API 封装
│   ├── cleaning_rules.py  数据清洗规则实现
│   ├── validators.py      数据校验器
│   └── alias_utils.py     人名别名映射工具
│
├── 📁 prompts/             文档和说明
│   └── README_prompt.md   详细任务说明
│
├── 📁 tests/               测试目录
│   ├── __init__.py
│   ├── test_cleaning.py   单元测试
│   ├── sample_raw.csv     样例原始数据
│   └── sample_aliases.csv 样例别名数据
│
├── 📁 logs/                日志和输出目录（运行时生成）
│   ├── clean_preview.csv  清洗预览（CSV 格式）
│   ├── clean_preview.json 清洗预览（JSON 格式）
│   └── validation_report_*.txt 校验报告
│
├── 📄 requirements.txt     Python 依赖
├── 📄 .gitignore          Git 忽略文件
├── 📄 run_pipeline.sh     🚀 便捷执行脚本
├── 📄 README.md           完整用户指南
├── 📄 QUICKSTART.md       快速上手指南
└── 📄 LICENSE             许可证
```

## 🔧 核心模块说明

### 1. clean_pipeline.py（主管线）

**职责**：协调整个清洗流程

**主要类**：
- `CleaningPipeline`：主管线类

**主要方法**：
- `read_source_data()`: 读取原始 Google Sheet
- `clean_data()`: 清洗数据
- `validate_data()`: 校验数据
- `write_output()`: 写入清洗结果
- `run()`: 执行完整流程

**流程**：
```
读取配置 → 读取原始表 → 列名映射 → 应用清洗规则 → 
别名映射 → 生成目标 Schema → 校验 → 输出（预览/写回）
```

### 2. gsheet_utils.py（Google Sheets 工具）

**职责**：封装 Google Sheets API 操作

**主要类**：
- `GSheetClient`：Google Sheets 客户端

**主要方法**：
- `read_range()`: 读取指定范围数据到 DataFrame
- `write_range()`: 写入 DataFrame 到指定范围
- `clear_range()`: 清空指定范围
- `append_rows()`: 追加数据

**特点**：
- 自动处理认证
- 支持从 URL 提取 Sheet ID
- 处理行长度不一致的情况

### 3. cleaning_rules.py（清洗规则）

**职责**：实现各种数据清洗和标准化规则

**主要类**：
- `CleaningRules`：清洗规则集合

**主要方法**：
- `clean_text()`: 文本清理（空格、占位符）
- `clean_date()`: 日期标准化
- `clean_scripture()`: 经文引用标准化
- `split_songs()`: 歌曲拆分
- `merge_columns()`: 列合并
- `get_service_week()`: 计算服务周数
- `infer_service_slot()`: 推断服务时段

**清洗规则**：
- 去除首尾空格（包括全角）
- 多空格合并为一个
- 占位符处理（`-`, `N/A` 等）
- 日期格式统一（YYYY-MM-DD）
- 歌曲拆分与去重

### 4. alias_utils.py（别名映射）

**职责**：处理人名别名，统一到稳定 ID

**主要类**：
- `AliasMapper`：别名映射器

**主要方法**：
- `load_from_sheet()`: 从 Google Sheet 加载别名
- `load_from_csv()`: 从 CSV 加载别名
- `resolve()`: 解析单个名字
- `resolve_list()`: 解析名字列表

**特点**：
- 不区分大小写
- 忽略空白字符
- 支持多对一映射
- 自动生成默认 ID

### 5. validators.py（校验器）

**职责**：数据校验和报告生成

**主要类**：
- `ValidationIssue`：校验问题记录
- `ValidationReport`：校验报告
- `DataValidator`：数据校验器

**校验规则**：
- 必填字段检查
- 日期格式验证
- 日期有效性验证
- 重复记录检测

**报告类型**：
- `error`：错误（阻止写入）
- `warning`：警告（不阻止写入）

## 🔄 数据流

```
┌─────────────────┐
│  原始 Google    │
│  Sheet          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  读取原始数据   │
│  (DataFrame)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  列名映射       │
│  (中文→英文)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  应用清洗规则   │◄─────│ 别名表       │
│  - 文本清理     │      │ (人名映射)   │
│  - 日期标准化   │      └──────────────┘
│  - 歌曲拆分     │
│  - 列合并       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  生成目标 Schema│
│  - person_id    │
│  - display_name │
│  - JSON 字段    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  数据校验       │
│  - 必填字段     │
│  - 日期格式     │
│  - 重复检测     │
└────────┬────────┘
         │
         ▼
    ┌────┴────┐
    │ dry-run?│
    └────┬────┘
         │
    ┌────┴────────┐
    │             │
    ▼             ▼
 [预览]       [写回清洗层]
CSV/JSON      Google Sheet
```

## 🎯 关键设计决策

### 1. 配置驱动

所有清洗规则和映射都通过 `config.json` 管理，无需修改代码即可调整。

**优点**：
- 灵活性高
- 易于维护
- 支持多环境

### 2. 模块化设计

每个模块职责清晰，松耦合：
- Google Sheets 操作独立
- 清洗规则可复用
- 校验逻辑分离

**优点**：
- 易于测试
- 易于扩展
- 代码复用

### 3. 别名映射

将多个别名映射到统一的 `person_id`，实现数据标准化。

**优点**：
- 数据一致性
- 支持多语言
- 便于后续分析

### 4. 双字段设计（ID + Name）

每个人员字段都包含 ID 和 Name：
- `preacher_id`, `preacher_name`
- `worship_lead_id`, `worship_lead_name`

**优点**：
- ID 稳定（用于关联）
- Name 可读（用于显示）

### 5. JSON 存储复杂字段

列表字段（如 `songs`, `worship_team_ids`）使用 JSON 格式存储。

**优点**：
- 结构清晰
- 易于解析
- 支持任意长度

### 6. Dry-run 模式

先预览后写入，降低风险。

**优点**：
- 安全性高
- 便于调试
- 避免错误数据

## 🧪 测试策略

### 单元测试

- **清洗规则测试**：测试各种边界情况
- **别名映射测试**：测试大小写、空格、未知名字
- **校验器测试**：测试各种错误场景

### 集成测试

使用样例数据（`tests/sample_raw.csv`）测试完整流程。

### 本地测试

无需 Google Sheet 即可用 CSV 测试逻辑。

## 🔒 安全考虑

### 最小权限原则

- 原始表：只读
- 清洗表：只写指定范围
- 别名表：只读

### 敏感信息保护

- 服务账号 JSON 不入库
- 使用环境变量
- 日志不打印令牌

## 📊 性能优化

### 批量操作

- 一次性读取整个范围
- 一次性写入所有数据

### 进度显示

使用 `tqdm` 显示清洗进度。

### 错误处理

- 单行错误不影响整体
- 详细记录错误位置和原因

## 🚀 扩展建议

### 短期

1. 添加更多日期格式支持
2. 支持自定义校验规则
3. 支持增量清洗（只处理新数据）

### 中期

1. 添加数据去重逻辑
2. 支持多个清洗层（分级清洗）
3. 添加数据统计分析

### 长期

1. 构建 Web UI
2. 支持实时清洗（监听原始表变化）
3. 集成到 Airflow/Prefect 等调度系统

## 📞 联系方式

如有问题或建议，请：
1. 查看文档：[README.md](README.md)
2. 查看测试用例：[tests/test_cleaning.py](tests/test_cleaning.py)
3. 提交 Issue（如果使用 GitHub）

---

**版本**：1.0.0  
**最后更新**：2025-10-06


