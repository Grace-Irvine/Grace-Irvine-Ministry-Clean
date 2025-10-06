# 快速调试指南 ⚡

> 无需连接 Google Sheets，使用本地 Excel 文件快速调试

## 🎯 目标

从本地 Excel 文件：
1. ✅ 提取所有人名，生成别名 CSV
2. ✅ 本地测试清洗逻辑
3. ✅ 调试配置和规则
4. ✅ 准备上传到 Google Sheets

## 📦 当前状态

✅ 已从 Excel 提取 **127 个唯一人名**  
✅ 已生成别名 CSV：`tests/generated_aliases.csv`  
📋 待办：编辑别名表，合并同一人的不同写法

## 🚀 三步快速开始

### 步骤 1：编辑别名表（**当前步骤**）

打开 `tests/generated_aliases.csv`，合并同一人的不同写法：

**示例**：

原始数据：
```csv
Zoey,person_zoey,Zoey,33,
Zoey Zhou,person_zoeyzhou,Zoey Zhou,16,
```

修改为：
```csv
Zoey,person_zoey_zhou,Zoey Zhou,33,
Zoey Zhou,person_zoey_zhou,Zoey Zhou,16,
```

**出现频率最高的前 20 位**（优先处理）：

```
 1. 王通    - 124 次
 2. 忠涵    -  61 次
 3. 靖铮    -  57 次
 4. 俊鑫    -  47 次
 5. Jimmy  -  44 次
 6. 张宇    -  36 次
 7. Zoey   -  33 次
 8. Gavin  -  33 次
 9. Daniel -  26 次
10. 赵超    -  22 次
11. 屈小煊   -  22 次
12. Enqi   -  18 次
13. 华亚西   -  18 次
14. Zoey Zhou - 16 次
15. 孙彤    -  14 次
16. 朱家霖   -  14 次
17. 亚西    -  13 次  ← 可能和"华亚西"是同一人
18. Weiwei -  13 次
19. 何凯    -  12 次
20. 周洪亮   -  11 次
```

**需要检查合并的**：
- `华亚西` (18次) + `亚西` (13次) → 可能是同一人
- `Zoey` (33次) + `Zoey Zhou` (16次) → 可能是同一人
- `Jason` (10次) + `Jason Yang` (11次) → 可能是同一人

### 步骤 2：本地测试清洗

```bash
python3 scripts/debug_clean_local.py \
    --excel "tests/Grace Irvine Sunday Worship All in One (1).xlsx" \
    --aliases tests/generated_aliases.csv \
    -o tests/debug_output.csv
```

**输出**：
- `tests/debug_output.csv` - 清洗后的数据
- `tests/debug_output.json` - JSON 格式
- 控制台显示校验报告

### 步骤 3：查看结果

```bash
# 用 Excel 或 Numbers 打开查看
open tests/debug_output.csv

# 或用命令行查看前几行
head -20 tests/debug_output.csv
```

检查：
- ✅ 日期格式是否正确（YYYY-MM-DD）
- ✅ 人员 ID 是否映射正确
- ✅ 显示名称是否统一
- ✅ 歌曲是否正确拆分

## 🔄 迭代流程

```
┌────────────────┐
│ 1. 编辑别名表   │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ 2. 运行测试清洗 │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ 3. 检查结果    │
└───────┬────────┘
        │
        ▼
  ┌─────┴──────┐
  │ 满意吗？    │
  └─────┬──────┘
        │
   ┌────┴────┐
   │ 否      │ 是
   │         │
   ▼         ▼
回步骤1    完成！✅
```

## 📝 常用命令

### 重新提取人名（如果需要）

```bash
python3 scripts/extract_aliases_smart.py \
    --excel "tests/Grace Irvine Sunday Worship All in One (1).xlsx" \
    -o tests/generated_aliases.csv
```

### 生成用于上传 Google Sheets 的版本

```bash
python3 scripts/extract_aliases_smart.py \
    --excel "tests/Grace Irvine Sunday Worship All in One (1).xlsx" \
    -o tests/aliases_for_sheets.csv \
    --no-count
```

（然后手动编辑，合并别名）

### 查看帮助

```bash
python3 scripts/extract_aliases_smart.py --help
python3 scripts/debug_clean_local.py --help
```

## 💡 编辑技巧

### 1. 使用 Excel 的筛选功能

1. 打开 `tests/generated_aliases.csv`
2. 选择表头行
3. 数据 → 筛选
4. 按 `count` 降序排序，优先处理高频人名

### 2. 使用查找替换批量修改

合并同一人时，批量替换 `person_id`：

1. Ctrl+H（Windows）或 Cmd+H（Mac）
2. 查找：`person_zoey`
3. 替换为：`person_zoey_zhou`
4. 全部替换

### 3. 添加备注

在 `note` 列标记角色：

```csv
alias,person_id,display_name,count,note
王通,person_wangtong,王通,124,牧师
```

## ❓ 常见问题

### Q: 如何知道哪些是同一人的不同写法？

A: 查看提示：
1. **相似的名字**：`华亚西` vs `亚西`
2. **全名 vs 简称**：`Zoey Zhou` vs `Zoey`
3. **英文 vs 中文**：需要人工判断

### Q: person_id 的命名规则是什么？

A: 建议：
- 英文：`person_firstname_lastname`（如 `person_zoey_zhou`）
- 中文：`person_拼音`（如 `person_wangtong`）
- 保持简洁、易读

### Q: 如果不确定是否同一人怎么办？

A: 
- **保守策略**：先不合并，保持独立
- 后续可以根据实际情况再调整

## 🎉 完成后

当本地调试满意后：

1. **更新 README**：记录最终的别名数量
2. **上传到 Google Sheets**：
   - 生成无统计列版本：`--no-count`
   - 上传到 Google Sheets
   - 更新 `config/config.json`
3. **运行正式管线**：
   ```bash
   ./run_pipeline.sh --dry-run
   ```

## 📚 详细文档

更多详细说明，请参考：
- [DEBUG_WORKFLOW.md](DEBUG_WORKFLOW.md) - 完整工作流程
- [README.md](README.md) - 用户指南
- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - 架构说明

---

**下一步**：编辑 `tests/generated_aliases.csv`，合并同一人的不同写法

