# 本地调试工作流程

本文档说明如何使用本地 Excel 文件进行调试，无需连接 Google Sheets。

## 📋 目录

1. [准备工作](#准备工作)
2. [步骤 1：提取人名生成别名表](#步骤-1提取人名生成别名表)
3. [步骤 2：编辑别名表](#步骤-2编辑别名表)
4. [步骤 3：本地测试清洗](#步骤-3本地测试清洗)
5. [步骤 4：上传到 Google Sheets](#步骤-4上传到-google-sheets)

## 🎯 准备工作

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

确保已安装 `openpyxl` 用于读取 Excel 文件。

### 2. 准备 Excel 文件

将原始 Google Sheet 导出为 Excel 格式，保存到 `tests/` 目录。

## 📝 步骤 1：提取人名生成别名表

### 运行提取脚本

```bash
python scripts/extract_aliases_smart.py \
    --excel "tests/Grace Irvine Sunday Worship All in One (1).xlsx" \
    -o tests/generated_aliases.csv
```

### 脚本功能

- ✅ 自动识别所有人名相关的列
- ✅ 提取并去重所有人名
- ✅ 统计每个人出现的次数
- ✅ 生成默认的 `person_id`
- ✅ 创建别名 CSV 文件

### 输出文件

`tests/generated_aliases.csv` 包含以下列：

| 列名 | 说明 | 示例 |
|-----|------|------|
| alias | 人名（别名） | 王通 |
| person_id | 默认生成的人员 ID | person_0001_wangtong |
| display_name | 显示名称 | 王通 |
| count | 出现次数 | 124 |
| note | 备注（空，供手动填写） |  |

## ✏️ 步骤 2：编辑别名表

### 打开 CSV 文件

使用 Excel、Numbers 或文本编辑器打开 `tests/generated_aliases.csv`。

### 合并同一人的不同写法

**示例**：假设同一人有多个写法

原始数据：
```csv
alias,person_id,display_name,count,note
华亚西,person_0123_huayaxi,华亚西,18,
亚西,person_0456_yaxi,亚西,13,
Yaxi,person_0789_yaxi,Yaxi,5,
```

编辑后：
```csv
alias,person_id,display_name,count,note
华亚西,person_huayaxi,华亚西,18,敬拜同工
亚西,person_huayaxi,华亚西,13,敬拜同工
Yaxi,person_huayaxi,华亚西,5,敬拜同工
```

**关键点**：
1. 将同一人的所有别名的 `person_id` 改为**相同值**
2. 将 `display_name` 设为**统一的首选名称**
3. 在 `note` 列添加角色或备注（可选）

### 常见合并场景

#### 1. 中文名 + 英文名

```csv
alias,person_id,display_name,count,note
张立军,person_zhanglijun,张立军,25,长老
Zhang Lijun,person_zhanglijun,张立军,5,长老
```

#### 2. 全名 + 简称

```csv
alias,person_id,display_name,count,note
屈小煊,person_quxiaoxuan,屈小煊,22,
小煊,person_quxiaoxuan,屈小煊,8,
```

#### 3. 英文名变体

```csv
alias,person_id,display_name,count,note
Jim 康康,person_jimkangkang,Jim 康康,44,
Jim,person_jimkangkang,Jim 康康,10,
康康,person_jimkangkang,Jim 康康,3,
```

### 编辑技巧

1. **按出现次数排序**：先处理出现频率高的人名
2. **使用查找替换**：批量修改 `person_id`
3. **添加备注**：在 `note` 列标记角色（牧师、长老、同工等）
4. **保持一致**：`display_name` 在所有行中应该一致

## 🧪 步骤 3：本地测试清洗

### 运行本地清洗脚本

```bash
python scripts/debug_clean_local.py \
    --excel "tests/Grace Irvine Sunday Worship All in One (1).xlsx" \
    --aliases tests/generated_aliases.csv \
    -o tests/debug_clean_output.csv
```

### 参数说明

| 参数 | 说明 | 默认值 |
|-----|------|--------|
| `--excel` | Excel 文件路径 | **必需** |
| `--aliases` | 别名 CSV 文件路径 | `tests/generated_aliases.csv` |
| `--config` | 配置文件路径 | `config/config.json` |
| `-o` / `--output` | 输出 CSV 路径 | `tests/debug_clean_output.csv` |
| `--json` | 输出 JSON 路径 | `tests/debug_clean_output.json` |

### 查看输出

脚本会生成：

1. **CSV 文件**：`tests/debug_clean_output.csv`
   - 清洗后的数据，可用 Excel 打开查看

2. **JSON 文件**：`tests/debug_clean_output.json`
   - 结构化数据，便于程序处理

3. **控制台输出**：
   - 清洗过程日志
   - 数据校验报告
   - 错误和警告信息

### 检查清洗结果

打开 `tests/debug_clean_output.csv`，检查：

✅ **日期格式**：是否统一为 `YYYY-MM-DD`  
✅ **人员 ID**：是否正确映射（如 `person_huayaxi`）  
✅ **显示名称**：是否使用统一名称（如 `华亚西`）  
✅ **歌曲拆分**：是否正确拆分为 JSON 数组  
✅ **空值处理**：空值是否正确处理

### 迭代调整

如果发现问题：

1. 回到步骤 2，继续编辑 `tests/generated_aliases.csv`
2. 或修改 `config/config.json` 中的清洗规则
3. 重新运行步骤 3 测试

重复这个过程直到清洗结果满意。

## 🚀 步骤 4：上传到 Google Sheets

### 4.1 准备上传版本的别名 CSV

生成不含 `count` 和 `note` 列的版本（用于上传到 Google Sheets）：

```bash
python scripts/extract_aliases_smart.py \
    --excel "tests/Grace Irvine Sunday Worship All in One (1).xlsx" \
    -o tests/aliases_for_upload.csv \
    --no-count
```

然后手动编辑 `tests/aliases_for_upload.csv`，合并别名（参考步骤 2）。

### 4.2 创建 Google Sheet

1. 在 Google Drive 中创建新的 Google Sheet
2. 命名为 "人名别名表" 或类似名称
3. 创建一个名为 `PeopleAliases` 的工作表

### 4.3 上传数据

方式 1：**手动复制粘贴**
1. 用 Excel 打开 `tests/aliases_for_upload.csv`
2. 复制所有数据（包括表头）
3. 粘贴到 Google Sheet 的 `PeopleAliases` 工作表

方式 2：**导入 CSV**
1. 在 Google Sheets 中：文件 → 导入
2. 选择 `tests/aliases_for_upload.csv`
3. 选择"替换当前工作表"

### 4.4 配置权限

1. 点击右上角的"共享"按钮
2. 将服务账号邮箱（如 `xxx@xxx.iam.gserviceaccount.com`）添加为**查看者**
3. 复制 Google Sheet 的 URL

### 4.5 更新配置文件

编辑 `config/config.json`，更新别名表配置：

```json
{
  "alias_sources": {
    "people_alias_sheet": {
      "url": "https://docs.google.com/spreadsheets/d/你的别名表ID/edit",
      "range": "PeopleAliases!A1:C"
    }
  }
}
```

### 4.6 测试正式管线

```bash
# 干跑模式测试
./run_pipeline.sh --dry-run

# 检查 logs/clean_preview.csv 是否正确

# 正式运行
./run_pipeline.sh
```

## 🔄 完整工作流程图

```
┌─────────────────────────────────────┐
│ 1. 导出 Google Sheet 为 Excel      │
│    └─> tests/data.xlsx             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. 运行提取脚本                     │
│    extract_aliases_smart.py        │
│    └─> tests/generated_aliases.csv │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. 手动编辑别名 CSV                 │
│    - 合并同一人的不同写法           │
│    - 统一 person_id                │
│    - 设置 display_name             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. 本地测试清洗                     │
│    debug_clean_local.py            │
│    └─> tests/debug_clean_output.csv│
└──────────────┬──────────────────────┘
               │
               ▼
       ┌───────┴────────┐
       │ 满意？         │
       └───────┬────────┘
               │
        ┌──────┴──────┐
        │ 否          │ 是
        ▼             ▼
  回到步骤 3      ┌─────────────────────────┐
  继续调整        │ 5. 上传别名表到 Google  │
                  │    Sheets               │
                  └──────────┬──────────────┘
                             │
                             ▼
                  ┌─────────────────────────┐
                  │ 6. 运行正式管线         │
                  │    ./run_pipeline.sh    │
                  └─────────────────────────┘
```

## 📋 快速参考命令

### 提取人名

```bash
# 生成带统计的版本（用于本地调试）
python scripts/extract_aliases_smart.py \
    --excel "tests/Grace Irvine Sunday Worship All in One (1).xlsx" \
    -o tests/generated_aliases.csv

# 生成用于上传的版本（不含统计列）
python scripts/extract_aliases_smart.py \
    --excel "tests/Grace Irvine Sunday Worship All in One (1).xlsx" \
    -o tests/aliases_for_upload.csv \
    --no-count
```

### 本地测试清洗

```bash
python scripts/debug_clean_local.py \
    --excel "tests/Grace Irvine Sunday Worship All in One (1).xlsx" \
    --aliases tests/generated_aliases.csv \
    -o tests/debug_clean_output.csv
```

### 正式运行

```bash
# 干跑模式
./run_pipeline.sh --dry-run

# 正式运行
./run_pipeline.sh
```

## 💡 提示和技巧

### 1. 使用版本控制

建议将编辑好的别名 CSV 提交到 Git：

```bash
git add tests/generated_aliases.csv
git commit -m "更新人名别名映射"
```

### 2. 备份重要文件

定期备份：
- `tests/generated_aliases.csv` - 别名映射
- `config/config.json` - 配置文件
- `tests/debug_clean_output.csv` - 清洗结果

### 3. 批量查找同一人

在编辑别名 CSV 时，可以使用以下方法查找同一人的不同写法：

1. 按姓氏分组查看
2. 查找相似的英文名（如 Zoey、Zoey Zhou）
3. 利用出现次数作为线索（频繁出现的人更重要）

### 4. 测试边界情况

在本地测试时，特别关注：
- 空值处理
- 特殊字符
- 多个分隔符的歌曲
- 日期格式变化

## ❓ 常见问题

### Q: 为什么有些人名没有被提取？

A: 可能的原因：
1. 该列不在预设的人名列表中
2. 人名格式特殊（如包含特殊符号）
3. 解决方法：检查 `extract_aliases_smart.py` 的 `people_keywords` 列表

### Q: 如何批量修改 person_id？

A: 使用 Excel 的查找替换功能：
1. 打开 CSV 文件
2. Ctrl+H（Windows）或 Cmd+H（Mac）
3. 查找旧 ID，替换为新 ID

### Q: 本地测试和正式运行有什么区别？

A: 
- **本地测试**：从 Excel 读取，写入本地 CSV
- **正式运行**：从 Google Sheets 读取，写入 Google Sheets

逻辑完全相同，只是数据源和目标不同。

### Q: 如何处理同名不同人的情况？

A: 在 `person_id` 中添加区分信息：
```csv
alias,person_id,display_name,note
李伟,person_liwei_worship,李伟,敬拜部
李伟,person_liwei_media,李伟,媒体部
```

## 📞 获取帮助

查看帮助信息：

```bash
python scripts/extract_aliases_smart.py --help
python scripts/debug_clean_local.py --help
```

---

**版本**：1.0.0  
**最后更新**：2025-10-06

