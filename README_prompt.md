# 数据清洗管线任务说明

> 本文档记录了数据清洗管线的完整需求和设计规范

## 🎯 任务目标（从原始层到清洗层）

构建一个可配置的数据清洗管线，用于将「教会主日事工安排」的原始 Google Sheet读取、清洗、标准化，并写入「清洗层 Google Sheet」。

**要求**：
- 只读原始层
- 只写清洗层
- 清洗规则受 config 管理
- 可本地干跑
- 产生日志与错误报告

## ✅ 交付成果

1. 可运行的 Python 项目（完整目录结构）
2. `config/config.json`（包含：原始/清洗 Sheet 链接、范围、列名映射、规则、别名数据源）
3. 脚本 `scripts/clean_pipeline.py`：执行读取→清洗→校验→写入
4. 日志与错误报告（写入 `logs/`；同时在控制台输出摘要）
5. 可选：`--dry-run` 模式仅输出 CSV/JSON 不写回清洗层

## 📁 目录结构

```
church-ministry-clean/
│
├── config/
│   └── config.json
│
├── scripts/
│   ├── clean_pipeline.py       # 主管线脚本
│   ├── gsheet_utils.py         # Google Sheets 工具
│   ├── cleaning_rules.py       # 清洗规则实现
│   ├── validators.py           # 数据校验器
│   └── alias_utils.py          # 别名映射工具
│
├── prompts/
│   └── README_prompt.md        # 本说明文档
│
├── tests/
│   ├── sample_raw.csv          # 样例原始数据
│   └── test_cleaning.py        # 单元测试
│
├── logs/
│   └── .gitkeep
│
├── .env.example                # 环境变量示例
├── requirements.txt            # Python 依赖
└── README.md                   # 用户文档
```

## ⚙️ 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 环境变量（使用服务账号；只赋最小权限）
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/sa.json"

# 干跑（不写回）
python scripts/clean_pipeline.py --config config/config.json --dry-run

# 正式写入清洗层
python scripts/clean_pipeline.py --config config/config.json
```

## 🧩 配置文件（config/config.json）

### 结构说明

1. **source_sheet**：原始表配置
   - `url`: Google Sheets URL
   - `range`: 数据范围（如 `RawData!A1:Z`）

2. **target_sheet**：清洗层配置
   - `url`: Google Sheets URL
   - `range`: 写入起始位置（如 `CleanData!A1`）

3. **columns**：列名映射
   - 将原始表的中文列名映射到标准英文列名

4. **cleaning_rules**：清洗规则
   - `date_format`: 日期格式（YYYY-MM-DD）
   - `strip_spaces`: 是否去除空格
   - `split_songs_delimiters`: 歌曲拆分分隔符列表
   - `merge_columns`: 需要合并的列
   - `role_whitelist`: 角色白名单（用于提示）

5. **alias_sources**：别名数据源
   - `people_alias_sheet`: 人名别名表配置
     - `url`: Google Sheets URL
     - `range`: 数据范围

6. **output_options**：输出选项
   - `overwrite`: 是否覆盖
   - `emit_csv_preview`: CSV 预览文件路径
   - `emit_json_preview`: JSON 预览文件路径

## 🧱 清洗层输出字段

清洗后的每一行描述一个**主日（或服务时段）**的完整"节目+同工汇总"记录。

### 字段列表（固定顺序）

```
service_date          主日日期 (YYYY-MM-DD)
service_week          服务周数 (ISO 周数)
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
worship_team_ids      敬拜同工 ID 列表 (JSON 数组)
worship_team_names    敬拜同工姓名列表 (JSON 数组)
pianist_id            司琴 ID
pianist_name          司琴姓名
songs                 诗歌列表 (JSON 数组或 "|" 分隔)
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

### 字段说明

- **ID/Name**：通过别名映射生成 `*_id`（稳定主键）与 `*_name`（展示名）
- **songs**：JSON 数组或管道分隔字符串，保持一致
- **service_week、service_slot**：可从日期/命名规则推导；无则留空
- **source_row**：记录原始表中的行号，便于追溯

## 🧪 规则与校验

### 清洗规则

1. **日期统一**：统一为 `YYYY-MM-DD` 格式
   - 非法日期记录到错误报告并跳过该行或标记错误状态

2. **姓名别名**：按 `alias_sources.people_alias_sheet` 将 "中文/英文/昵称" 归并到稳定 `person_id` 与首选显示名

3. **空值/占位符**：如 `-`、`N/A`、空白 → 统一为空字符串

4. **空白清理**：中英文空格、全角空格统一去除首尾、多空格合一

5. **歌曲**：按多分隔符拆分、去重、去首尾空白

6. **经文**：可做轻量规范化（可选：解析"书-章:节-节"）

7. **合并列**：`worship_team = [worship_team_1, worship_team_2]`，过滤空值

8. **角色白名单**：若需要，校验是否属于 `role_whitelist`（当前用于提示，非硬限制）

### 校验规则

1. **必填字段**：`service_date` 必须有值
2. **日期格式**：必须符合 `YYYY-MM-DD` 格式
3. **重复检测**：同 `service_date + service_slot` 重复 → 记录 warning

## 🧰 代码实现要点

### 技术栈

- **Google Sheets API**：`google-api-python-client` + `google-auth`
- **数据处理**：`pandas`
- **日期解析**：`python-dateutil`
- **测试**：`pytest`

### 模块职责

1. **gsheet_utils.py**：封装读取二维数组→DataFrame、写入 DataFrame 到目标范围（覆盖/追加）

2. **cleaning_rules.py**：实现字符串清理、日期规范、经文规范、歌曲拆分合并、列合并等

3. **alias_utils.py**：载入人名别名表（`[alias, person_id, display_name]`），对所有姓名字段做映射

4. **validators.py**：数据校验器，生成错误和警告报告

5. **clean_pipeline.py**：主管线
   - 读取 config
   - 拉取原始表 → DataFrame
   - 基于 columns 做列映射与重命名
   - 应用 cleaning rules & alias 映射
   - 生成目标列顺序、补充 `updated_at`、`source_row`
   - 校验并汇总错误/警告
   - `--dry-run`：导出预览 CSV/JSON；否则写回清洗层范围
   - 输出日志摘要（总行数、成功、警告、错误）并将明细写入 `logs/`

### 权限与安全

- **最小权限**：原始表只读；清洗表只写对应范围
- **使用服务账号**
- **禁止把服务账号 JSON 提交到仓库**；提供 `.env.example` 说明
- **日志中禁止打印敏感令牌**与完整 URL 的 token 参数

## 🔎 样例：从原始到清洗

### 原始行（示意）

```
主日日期=2025/10/05
讲道标题=主里合一
经文=以弗所书 4:1-6
讲员=张牧师
讲道系列=以弗所书系列
要理问答=第37问
读经=诗篇133
敬拜带领=王丽
敬拜同工1=陈明
敬拜同工2=林芳
司琴=李伟
詩歌=奇异恩典 / 我心灵得安宁
音控=赵强
导播/摄影=周晨
ProPresenter播放=黄立
ProPresenter更新=李慧
助教=刘丹
```

### 清洗后（示意 JSON，一行）

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
  "worship_team_ids": ["person_chenming","person_linfang"],
  "worship_team_names": ["陈明","林芳"],
  "pianist_id": "person_liwei",
  "pianist_name": "李伟",
  "songs": ["奇异恩典","我心灵得安宁"],
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
  "source_row": 12,
  "updated_at": "2025-10-06T10:00:00Z"
}
```

## ✔️ 验收标准

脚本结束时应打印：

```
============================================================
数据校验报告
============================================================
总行数: N
成功行数: M
警告行数: W
错误行数: E

错误 (前 5 条):
  行 15 | service_date: 日期格式不正确
  ...

警告 (前 5 条):
  行 20 | service_date: 重复的服务记录
  ...
============================================================

✅ 读取原始表成功：N 行
✅ 清洗成功行：M 行
⚠️  警告行：W 行
❌ 错误行：E 行
✅ 目标表写入成功（若非 dry-run）：M 行
✅ 生成预览文件：logs/clean_preview.csv, logs/clean_preview.json
✅ 生成详细报告：logs/validation_report_YYYYMMDD_HHMMSS.txt
```

**返回码**：
- `0`：成功（无致命错误）
- `1`：有致命错误

## 🧪 测试要求

### 测试数据

- **tests/sample_raw.csv**：包含 5–10 行，覆盖：
  - 日期格式不一致
  - 空白
  - 歌曲分隔
  - 多别名
  - 无效日期（测试错误处理）

- **tests/sample_aliases.csv**：人名别名映射数据

### 单元测试（tests/test_cleaning.py）

测试内容：
- ✅ 日期规范化
- ✅ 别名映射
- ✅ 歌曲拆分合并
- ✅ 列合并
- ✅ 文本清理
- ✅ 数据校验

本地可在无 GSheet 环境下，用 CSV 读写跑通逻辑；集成测试再连真实 Sheet。

## 📦 依赖

```
pandas>=2.2
python-dateutil>=2.9
google-api-python-client>=2.149
google-auth>=2.34
google-auth-oauthlib>=1.2
tqdm>=4.66
tabulate>=0.9
pytest>=8.3
```

## 📝 代码质量要求

- ✅ 结构清晰
- ✅ 函数带类型注解
- ✅ 关键步骤有 docstring 与注释
- ✅ 出错要抛出带明确信息的异常
- ✅ 在主流程收敛为人类可读报告

## 🔐 安全与最小权限

- ✅ 使用服务账号
- ✅ 权限：原始表只读、清洗表只写对应范围
- ❌ 禁止把服务账号 JSON 提交到仓库；提供 `.env.example` 说明
- ❌ 日志中禁止打印敏感令牌与完整 URL 的 token 参数

---

**生成时间**：2025-10-06  
**版本**：1.0


