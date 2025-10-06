# 教会主日事工数据清洗管线

一个可配置的数据清洗管线，用于将教会主日事工安排的原始 Google Sheet 数据进行清洗、标准化，并写入清洗层 Google Sheet。

## 📚 文档导航

| 文档 | 描述 | 适用人群 |
|-----|------|----------|
| [README.md](README.md)（本文档） | 完整用户指南和技术文档 | 所有用户 |
| [QUICKSTART.md](QUICKSTART.md) | ⚡ 5 分钟快速上手指南 | 新用户 |
| [QUICK_DEBUG_GUIDE.md](QUICK_DEBUG_GUIDE.md) | 🔧 本地调试快速指南 | **调试人员** |
| [DEBUG_WORKFLOW.md](DEBUG_WORKFLOW.md) | 🛠️ 完整调试工作流程 | **调试人员** |
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | 📦 项目交付总结 | 项目管理者 |
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | 🏗️ 项目架构和设计 | 开发者 |
| [CHANGELOG.md](CHANGELOG.md) | 📝 版本历史 | 所有用户 |
| [prompts/README_prompt.md](prompts/README_prompt.md) | 📋 详细任务说明 | 开发者 |

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

- **可配置的清洗规则**：通过 JSON 配置文件管理所有清洗规则
- **人名别名映射**：支持将多个别名（中文名、英文名、昵称）映射到统一的人员 ID
- **多种日期格式支持**：自动识别并标准化多种日期格式
- **智能文本清理**：去除空白、处理占位符、标准化空格
- **歌曲拆分与去重**：支持多种分隔符，自动去重
- **数据校验**：生成详细的错误和警告报告
- **Dry-run 模式**：可先预览清洗结果，不写回 Google Sheet
- **详细日志**：记录所有操作和问题

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆仓库
cd church-ministry-clean

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 配置 Google 服务账号

1. 在 [Google Cloud Console](https://console.cloud.google.com/) 创建服务账号
2. 下载服务账号的 JSON 密钥文件
3. 设置环境变量：

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account.json"
```

4. 为服务账号分配权限：
   - 原始表：查看者（Viewer）权限
   - 清洗表：编辑者（Editor）权限

### 3. 配置清洗管线

编辑 `config/config.json`，填入：
- 原始表和清洗表的 Google Sheets URL
- 列名映射
- 别名数据源（可选）

### 4. 运行管线

```bash
# 干跑模式（仅生成预览，不写回）
python scripts/clean_pipeline.py --config config/config.json --dry-run

# 正式运行（写入清洗层）
python scripts/clean_pipeline.py --config config/config.json
```

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

- 📖 [QUICK_DEBUG_GUIDE.md](QUICK_DEBUG_GUIDE.md) - 快速指南
- 📖 [DEBUG_WORKFLOW.md](DEBUG_WORKFLOW.md) - 完整工作流程

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
church-ministry-clean/
│
├── config/
│   └── config.json              # 配置文件
│
├── scripts/
│   ├── clean_pipeline.py        # 主清洗管线
│   ├── gsheet_utils.py          # Google Sheets 工具
│   ├── cleaning_rules.py        # 清洗规则
│   ├── validators.py            # 数据校验器
│   └── alias_utils.py           # 别名映射工具
│
├── prompts/
│   └── README_prompt.md         # 任务说明文档
│
├── tests/
│   ├── sample_raw.csv           # 样例原始数据
│   ├── sample_aliases.csv       # 样例别名数据
│   └── test_cleaning.py         # 单元测试
│
├── logs/
│   ├── clean_preview.csv        # 清洗预览 (CSV)
│   ├── clean_preview.json       # 清洗预览 (JSON)
│   └── validation_report_*.txt  # 校验报告
│
├── .gitignore                   # Git 忽略文件
├── requirements.txt             # Python 依赖
└── README.md                    # 本文档
```

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
