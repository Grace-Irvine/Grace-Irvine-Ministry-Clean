# 自动别名同步完整指南

## 📋 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [工作原理](#工作原理)
- [配置说明](#配置说明)
- [使用方法](#使用方法)
- [人工审核流程](#人工审核流程)
- [常见问题](#常见问题)

---

## 概述

自动别名同步功能会在每次运行数据清洗管道时，自动检测新增的同工名字，并将其添加到 Google Sheets 的 `generated_aliases` 工作表中，同时更新所有名字的出现次数统计。

### 核心特性

✅ **自动检测**：新同工名单自动识别  
✅ **自动添加**：无需手动创建条目  
✅ **统计更新**：出现次数实时更新  
✅ **人工审核**：保留最终决策权  
✅ **错误容忍**：不影响主流程  
✅ **完整文档**：详细的使用说明

---

## 快速开始

### 🚀 5 分钟上手

#### 第一步：确认配置

检查 `config/config.json`：

```bash
# 查看配置
cat config/config.json | grep -A 20 "alias_sources"
```

确保有这些配置：
```json
{
  "alias_sources": {
    "auto_sync": true,        // ✅ 必须是 true
    "include_count": true,
    "role_fields": [...]
  }
}
```

#### 第二步：运行单元测试（可选）

```bash
# 验证功能正常
python3 test_alias_mapper_unit.py
```

期望输出：
```
测试结果: 4 通过, 0 失败
```

#### 第三步：运行清洗管道

```bash
# 正常运行（会写入数据）
python core/clean_pipeline.py --config config/config.json

# 或者干跑模式（不写入，仅测试）
python core/clean_pipeline.py --config config/config.json --dry-run
```

#### 第四步：查看结果

观察日志输出：

```
============================================================
开始自动同步别名...
从数据中提取了 XX 个唯一人名
检测到 X 个新名字，XX 个已存在名字
✅ 别名同步完成！
   📊 新增: X 个名字
   📊 更新: XX 个名字的统计
============================================================
💡 提示: 请在 Google Sheets 中检查新增的名字
   3. 表格链接: https://docs.google.com/spreadsheets/d/...
============================================================
```

#### 第五步：人工审核

1. 打开上面的 Google Sheets 链接
2. 查看 `generated_aliases` 工作表
3. 找到新增的行（检查 `count` 列）
4. 编辑 `person_id` 合并同一人的不同写法
5. 编辑 `display_name` 设置统一显示名

---

## 工作原理

### 1. 自动检测
- 在数据清洗完成后，系统自动扫描所有角色字段中的人名
- 统计每个人名的出现次数
- 区分新名字和已存在的名字

### 2. 同步到 Google Sheets
- **新名字**：自动添加新行，包含：
  - `alias`: 原始名字
  - `person_id`: 自动生成的默认ID（格式：`person_{normalized_name}`）
  - `display_name`: 默认使用原始名字
  - `count`: 出现次数
  
- **已有名字**：更新 `count` 列的统计数据

### 3. 人工审核
系统会提示您在 Google Sheets 中：
1. 检查新增的名字
2. 合并同一人的不同写法（通过修改 `person_id` 为相同值）
3. 设置统一的 `display_name`

### 工作流程图

```
1. 运行清洗管道
   ↓
2. 数据清洗完成
   ↓
3. 自动提取所有人名
   ↓
4. 区分新名字 vs 已存在
   ↓
5. 同步到 Google Sheets
   - 新名字：添加新行
   - 已有名字：更新 count
   ↓
6. 输出统计报告
   ↓
7. 提示人工审核
```

---

## 配置说明

### 配置文件结构

在 `config/config.json` 中的 `alias_sources` 部分：

```json
{
  "alias_sources": {
    "people_alias_sheet": {
      "url": "Google Sheets URL",
      "range": "generated_aliases!A1:D"
    },
    "auto_sync": true,
    "include_count": true,
    "role_fields": [
      "preacher",
      "reading",
      "worship_lead",
      "worship_team_1",
      "worship_team_2",
      "pianist",
      "audio",
      "video",
      "propresenter_play",
      "propresenter_update",
      "video_editor",
      "assistant_1",
      "assistant_2",
      "assistant_3"
    ]
  }
}
```

### 配置参数说明

- `auto_sync`: 是否启用自动同步（默认：`true`）
- `include_count`: 是否包含统计列（默认：`true`）
- `role_fields`: 需要提取人名的角色字段列表
- `range`: Google Sheets 范围，必须包含 4 列（A-D）

### Google Sheets 表结构

`generated_aliases` 工作表应包含以下列：

| 列 | 名称 | 说明 | 自动更新 |
|----|------|------|---------|
| A | alias | 别名（原始人名） | ✅ |
| B | person_id | 人员ID | ⚠️ 需人工编辑 |
| C | display_name | 显示名称 | ⚠️ 需人工编辑 |
| D | count | 出现次数 | ✅ |

---

## 使用方法

### 正常运行（自动同步）

```bash
python core/clean_pipeline.py --config config/config.json
```

如果启用了 `auto_sync`，系统会在数据清洗完成后自动同步别名。

### 测试同步功能

```bash
python test_alias_sync.py
```

此命令会：
1. 运行清洗管道（干跑模式）
2. 执行别名同步
3. 输出统计信息

### 禁用自动同步

在 `config.json` 中设置：

```json
{
  "alias_sources": {
    "auto_sync": false
  }
}
```

### 常用命令

```bash
# 单元测试（不连接 Google Sheets）
python3 test_alias_mapper_unit.py

# 集成测试（连接 Google Sheets，干跑模式）
python3 test_alias_sync.py

# 正常运行（会写入所有数据）
python core/clean_pipeline.py

# 干跑模式（仅预览，不写入清洗层）
python core/clean_pipeline.py --dry-run

# 查看别名配置
python3 -c "
import json
with open('config/config.json') as f:
    config = json.load(f)
    print('自动同步:', config['alias_sources'].get('auto_sync', False))
    print('角色数量:', len(config['alias_sources'].get('role_fields', [])))
"
```

---

## 人工审核流程

### 1. 检查新增名字

运行清洗管道后，查看日志中的统计信息：

```
✅ 别名同步完成！
   📊 新增: 3 个名字
   📊 更新: 25 个名字的统计
   📊 总计: 28 个唯一人名
```

### 2. 打开 Google Sheets

访问配置中的 URL，查看 `generated_aliases` 工作表。

### 3. 合并重复人名

**示例：修改前**
| alias | person_id | display_name | count |
|-------|-----------|--------------|-------|
| 张立军 | person_张立军 | 张立军 | 15 |
| Zhang Lijun | person_zhanglijun | Zhang Lijun | 3 |
| 张牧师 | person_张牧师 | 张牧师 | 8 |

**修改后**
| alias | person_id | display_name | count |
|-------|-----------|--------------|-------|
| 张立军 | zhang_lijun | 张立军牧师 | 15 |
| Zhang Lijun | zhang_lijun | 张立军牧师 | 3 |
| 张牧师 | zhang_lijun | 张立军牧师 | 8 |

> 💡 **关键**: 将同一人的所有别名的 `person_id` 改为相同值

### 4. 重新运行清洗

修改完成后，重新运行清洗管道，系统会使用更新后的别名映射。

---

## 重要特性

### 幂等性
多次运行同一数据集不会重复添加名字，只会更新统计数据。

### 错误容忍
如果别名同步失败，不会影响数据清洗流程。系统会记录警告日志并继续执行。

### 增量更新
- 新名字自动添加
- 已有名字的统计自动更新
- 人工编辑的 `person_id` 和 `display_name` 不会被覆盖

---

## 常见问题

### Q: 如何临时禁用自动同步？

A: 在 `config.json` 中设置 `alias_sources.auto_sync = false`。

### Q: 同步失败怎么办？

A: 检查：
1. Google Sheets 权限是否正确
2. 服务账号凭证是否有效
3. 工作表名称和范围是否正确
4. 网络连接是否正常

```bash
# 检查服务账号
ls -la config/service-account.json

# 测试连接
python3 -c "
from core.gsheet_utils import GSheetClient
client = GSheetClient()
print('✅ 连接成功')
"
```

### Q: 没有看到新名字？

A: **症状**: 日志显示 "新增: 0 个名字"

**原因**: 所有名字都已存在

**验证**:
```bash
# 运行单元测试，使用测试数据
python3 test_alias_mapper_unit.py
```

### Q: 可以手动触发同步吗？

A: 可以使用测试脚本：

```bash
python test_alias_sync.py
```

### Q: 如何修改默认的 person_id 格式？

A: 编辑 `core/alias_utils.py` 中的 `sync_to_sheet` 方法，修改这一行：

```python
person_id = f"person_{normalized}"
```

---

## 最佳实践

### 1. 定期审核

建议每周检查一次 Google Sheets，审核新增的名字。

### 2. 命名规范

为 `person_id` 建立统一规范：
- 英文名：小写，下划线连接（如 `john_doe`）
- 中文名：拼音，下划线连接（如 `zhang_lijun`）
- 特殊情况：添加后缀区分（如 `zhang_san_elder`）

### 3. 显示名规范

为 `display_name` 建立统一规范：
- 优先使用中文全名
- 可添加职位后缀（如 "张立军牧师"）
- 保持一致性

### 4. 及时处理

新增名字后尽快审核，避免累积过多待处理条目。

### 5. 备份数据

定期导出 `generated_aliases` 工作表作为备份。

---

## 技术细节

### 名字标准化

系统使用 `_normalize_for_matching` 方法来标准化名字，用于匹配查找：

- 去除所有空白字符（包括全角空格）
- 转换为小写
- 用于检测重复，但不影响显示

### 角色字段映射

系统在清洗后的数据中查找以 `_name` 结尾的列：

- `preacher` → `preacher_name`
- `worship_lead` → `worship_lead_name`
- 等等

### 统计算法

每个人名的出现次数是通过扫描所有配置的角色字段计算的。如果同一个人在一次主日中担任多个角色，会被计算多次。

### 核心实现

#### AliasMapper 类扩展 (`core/alias_utils.py`)

新增了三个关键方法：

1. **`extract_names_from_cleaned_data(df, role_fields)`**
   - 从清洗后的 DataFrame 中提取所有人名
   - 统计每个人名的出现次数
   - 返回 Counter 对象

2. **`detect_new_and_existing(names_counter)`**
   - 区分新名字和已存在的名字
   - 基于 `alias_map` 进行匹配
   - 返回两个列表：(新名字, 已存在名字)

3. **`sync_to_sheet(client, url, range_name, names_counter)`**
   - 读取现有的 Google Sheets 数据
   - 对新名字：添加新行（默认 person_id, display_name, count）
   - 对已有名字：更新 count 列
   - 写回 Google Sheets

#### CleaningPipeline 集成 (`core/clean_pipeline.py`)

1. **`_sync_aliases(clean_df)`** 方法
   - 在数据清洗完成后自动调用
   - 提取所有角色字段的人名
   - 调用 AliasMapper 的同步功能
   - 输出详细的统计日志

2. **集成到清洗流程**
   - 在 `clean_data()` 方法返回前调用
   - 仅在 `auto_sync = true` 时执行
   - 错误容忍：同步失败不影响主流程

---

## 日志示例

### 成功运行

```
============================================================
开始自动同步别名...
从数据中提取了 28 个唯一人名
检测到 3 个新名字，25 个已存在名字
开始同步别名到 Google Sheets...
读取到 25 条现有记录
✅ 成功同步到 Google Sheets
   新增: 3 个名字
   更新: 25 个名字的统计
============================================================
✅ 别名同步完成！
   📊 新增: 3 个名字
   📊 更新: 25 个名字的统计
   📊 总计: 28 个唯一人名
============================================================
💡 提示: 请在 Google Sheets 中检查新增的名字
   1. 合并同一人的不同写法（修改 person_id）
   2. 设置统一的 display_name
   3. 表格链接: https://docs.google.com/spreadsheets/d/...
============================================================
```

---

## 相关文件

- `core/alias_utils.py` - 别名映射核心逻辑
- `core/clean_pipeline.py` - 清洗管道集成
- `config/config.json` - 配置文件
- `test_alias_sync.py` - 测试脚本
- `test_alias_mapper_unit.py` - 单元测试

---

## 🎉 开始使用

```bash
# 一键运行
python core/clean_pipeline.py
```

就这么简单！系统会自动：
- ✅ 清洗数据
- ✅ 提取人名
- ✅ 同步到 Google Sheets
- ✅ 更新统计
- ✅ 提示你审核

剩下的就是打开 Google Sheets，审核新名字，完成！

---

**版本**: 1.0  
**最后更新**: 2025-10-13  
**状态**: ✅ 生产可用
