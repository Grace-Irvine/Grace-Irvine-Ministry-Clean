# 生成同工元数据表指南

## ⚠️ 重要前提条件

**在运行脚本之前，必须先在 Google Sheets 中创建 `VolunteerMetadata` sheet！**

### 创建步骤：

1. 打开 Google Sheets：
   ```
   https://docs.google.com/spreadsheets/d/1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc/edit
   ```

2. 点击左下角的 "+" 按钮，创建新 sheet

3. 将新 sheet 重命名为：`VolunteerMetadata`

4. 在第一行添加表头（8个列，按顺序）：
   ```
   person_id | person_name | family_group | unavailable_start | unavailable_end | unavailable_reason | notes | updated_at
   ```

5. 完成！现在可以运行脚本了

---

## 📋 脚本功能

`scripts/generate_volunteer_metadata.py` 会自动：

1. ✅ 从 alias 表读取所有人员的 person_id 和 display_name
2. ✅ 检查是否有重名情况（同一个 display_name 对应多个 person_id）
3. ✅ 自动填充前3列：
   - `person_id`
   - `person_name`（使用 alias 表的 display_name）
   - `updated_at`（当前日期）
4. ✅ 保留已有的其他列数据（如果表已存在）
5. ✅ 写入 Google Sheets

---

## 🚀 使用方法

### 方式 A: 使用快速脚本（推荐）

```bash
# 预览模式
./run_generate_metadata.sh --dry-run

# 实际写入
./run_generate_metadata.sh
```

### 方式 B: 直接运行 Python 脚本

首先设置环境变量：
```bash
export GOOGLE_APPLICATION_CREDENTIALS="config/service-account.json"
```

### 步骤 1: 预览模式（推荐先运行）

```bash
python3 scripts/generate_volunteer_metadata.py --dry-run
```

这会：
- ✅ 读取 alias 表
- ✅ 检查重名
- ✅ 显示将要生成的数据（前5条）
- ❌ **不写入** Google Sheets

**预期输出**：
```
====================================
生成同工元数据表
====================================
读取别名表: https://docs.google.com/spreadsheets/d/...
别名表共有 150 条记录
提取到 45 个唯一人员
✅ 无重名情况
创建新的元数据表
生成 45 条新记录
🔍 Dry-run 模式：不写入 Google Sheets
预览前5条记录：
   person_id        person_name family_group unavailable_start ...
0  person_8101_谢苗  谢苗                                        ...
1  person_9017_屈小煊 屈小煊                                       ...
...
```

---

### 步骤 2: 正式写入

确认预览无误后，执行写入：

```bash
python3 scripts/generate_volunteer_metadata.py
```

这会：
- ✅ 在 Google Sheets 中创建/更新 `VolunteerMetadata` 表
- ✅ 填充前3列（person_id, person_name, updated_at）
- ✅ 保留其他列为空，等待你手动填写

**预期输出**：
```
====================================
生成同工元数据表
====================================
读取别名表: https://docs.google.com/spreadsheets/d/...
别名表共有 150 条记录
提取到 45 个唯一人员
✅ 无重名情况
创建新的元数据表
生成 45 条新记录
写入元数据到 Google Sheets: https://...
✅ 成功写入 45 条记录到 Google Sheets

====================================
✅ 完成！
====================================
总人数: 45

📝 下一步：
  1. 打开 Google Sheets 查看生成的数据
  2. 手动填写 family_group（家庭关系）
  3. 手动填写 unavailable_start/end（不可用时间段）
  4. 手动填写 notes（备注信息）

Google Sheets URL: https://...
====================================
```

---

## 📊 生成的数据结构

脚本会生成以下列（表头自动创建）：

| 列名 | 自动填充 | 说明 |
|------|---------|------|
| person_id | ✅ 是 | 从 alias 表提取 |
| person_name | ✅ 是 | 使用 alias 表的 display_name |
| family_group | ❌ 否 | **需要手动填写** - 家庭组ID（如 family_xie_qu） |
| unavailable_start | ❌ 否 | **需要手动填写** - 不可用开始日期 |
| unavailable_end | ❌ 否 | **需要手动填写** - 不可用结束日期 |
| unavailable_reason | ❌ 否 | **需要手动填写** - 不可用原因 |
| notes | ❌ 否 | **需要手动填写** - 其他备注 |
| updated_at | ✅ 是 | 自动设置为当前日期 |

---

## 🔄 更新场景

### 场景 1: 首次创建表格

```bash
python3 scripts/generate_volunteer_metadata.py
```

- ✅ 创建新表，填充所有人员的基础信息
- ✅ 其他列为空，等待手动填写

---

### 场景 2: 添加了新同工

当 alias 表中添加了新同工后：

```bash
python3 scripts/generate_volunteer_metadata.py
```

- ✅ 保留现有记录的所有数据（包括手动填写的部分）
- ✅ 只添加新同工的基础信息
- ✅ 更新所有人的 updated_at

**示例**：
```
现有元数据表共有 45 条记录
提取到 48 个唯一人员
合并新旧数据...
✅ 更新了 45 条现有记录
✅ 添加了 3 条新记录
✅ 总共 48 条记录
```

---

### 场景 3: 修改了 display_name

当在 alias 表中修改了某人的 display_name：

```bash
python3 scripts/generate_volunteer_metadata.py
```

- ✅ 自动更新 metadata 表中的 person_name
- ✅ 保留其他所有手动填写的数据
- ✅ 更新 updated_at

---

## ⚠️ 重名检测

如果脚本检测到重名，会显示警告：

```
⚠️  发现重名的情况：
  - 张三: 2次
    • person_1234_张三
    • person_5678_张三
  建议在 alias 表中修改 display_name 以区分重名人员
```

**解决方法**：
1. 打开 alias 表
2. 找到重名的记录
3. 修改 display_name 为：
   - `张三（早场）` 和 `张三（晚场）`
   - 或 `张三 Sr.` 和 `张三 Jr.`
   - 或其他能区分的名称
4. 重新运行脚本

---

## 📝 手动填写指南

### 1. family_group（家庭关系）

**用途**：标识同一家庭的成员，防止同一周安排多个家庭成员服侍

**填写方法**：
- 夫妻：`family_xie_qu`（谢苗和屈小煊）
- 家庭：`family_du`（杜家的所有人）
- 不是家庭成员：留空

**示例**：
```
person_8101_谢苗    → family_xie_qu
person_9017_屈小煊  → family_xie_qu
person_3850_靖铮    → （留空，无家庭成员）
```

---

### 2. unavailable_start / unavailable_end（不可用时间段）

**用途**：记录同工不能服侍的时间段

**填写方法**：
- 格式：`YYYY-MM-DD`
- 单次不可用：填写开始和结束日期
- 多段不可用：添加多行，person_id 相同

**示例**：
```csv
person_id,person_name,unavailable_start,unavailable_end,unavailable_reason
person_8101_谢苗,谢苗,2024-11-01,2024-11-15,旅行
person_3850_靖铮,靖铮,2024-12-20,2024-12-31,回国探亲
```

**多段不可用（同一人）**：
```csv
person_6878_杜德双,杜德双,2024-10-15,2024-10-20,出差
person_6878_杜德双,杜德双,2024-11-10,2024-11-12,参加会议
```

---

### 3. notes（备注）

**用途**：记录其他重要信息

**示例**：
```
优先安排早场
擅长音控
不适合视频岗位
与谢苗是夫妻
```

---

## 🔗 命令选项

```bash
python3 scripts/generate_volunteer_metadata.py [选项]

选项：
  --config PATH    指定配置文件（默认: config/config.json）
  --dry-run        预览模式，不写入 Google Sheets
  -h, --help       显示帮助信息
```

**示例**：
```bash
# 使用自定义配置
python3 scripts/generate_volunteer_metadata.py --config /path/to/config.json

# 预览模式
python3 scripts/generate_volunteer_metadata.py --dry-run
```

---

## ✅ 完整工作流程

### 首次使用

```bash
# 1. 预览
python3 scripts/generate_volunteer_metadata.py --dry-run

# 2. 确认无误后写入
python3 scripts/generate_volunteer_metadata.py

# 3. 打开 Google Sheets
# https://docs.google.com/spreadsheets/d/1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc/edit

# 4. 手动填写 family_group, unavailable_*, notes

# 5. 测试 API
curl "http://localhost:8080/api/v1/volunteer/metadata" | jq
```

### 后续更新

```bash
# 添加新同工后，直接运行
python3 scripts/generate_volunteer_metadata.py

# 会自动：
# - 保留现有数据
# - 添加新同工
# - 更新时间戳
```

---

## 📊 数据验证

脚本完成后，可以验证数据：

```bash
# 1. 获取元数据
curl "http://localhost:8080/api/v1/volunteer/metadata" | jq

# 2. 检查人数
curl "http://localhost:8080/api/v1/volunteer/metadata" | jq '.metadata.total_count'

# 3. 查看特定人员
curl "http://localhost:8080/api/v1/volunteer/metadata?person_id=person_8101_谢苗" | jq
```

---

## 🔧 故障排除

### 问题 1: 找不到 alias 表

**错误**：`配置文件中缺少 alias_sources`

**解决**：检查 `config/config.json` 中是否有 `alias_sources.people_alias_sheet` 配置

---

### 问题 2: 权限错误

**错误**：`Permission denied`

**解决**：
1. 检查服务账号是否有 Google Sheets 的编辑权限
2. 确认 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量已设置

---

### 问题 3: 重名警告

**警告**：`发现重名的情况`

**解决**：
1. 在 alias 表中修改 display_name 以区分
2. 添加后缀或标识符，如：
   - `张三（A堂）` / `张三（B堂）`
   - `张三 Sr.` / `张三 Jr.`

---

## 📚 相关文档

- [VOLUNTEER_METADATA_SETUP_GUIDE.md](VOLUNTEER_METADATA_SETUP_GUIDE.md) - 完整设置指南
- [docs/GOOGLE_SHEETS_SETUP.md](docs/GOOGLE_SHEETS_SETUP.md) - Google Sheets 详细说明
- [docs/VOLUNTEER_METADATA_ANALYSIS.md](docs/VOLUNTEER_METADATA_ANALYSIS.md) - 需求分析

---

**准备好了吗？开始吧！** 🚀

```bash
python3 scripts/generate_volunteer_metadata.py --dry-run
```

