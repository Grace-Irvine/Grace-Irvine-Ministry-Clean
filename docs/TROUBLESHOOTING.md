# 故障排除指南 🔧

根据你遇到的错误，这里是详细的解决方案。

## 🚨 当前错误

### 错误 1：别名表权限不足（403 Forbidden）

```
The caller does not have permission
```

**原因**：服务账号没有访问别名表的权限

**解决方案**：

1. **找到服务账号邮箱**：
   ```bash
   # 从服务账号 JSON 文件中提取邮箱
   cat "$GOOGLE_APPLICATION_CREDENTIALS" | grep client_email
   ```
   
   会显示类似：`"client_email": "xxx@xxx.iam.gserviceaccount.com"`

2. **添加权限到别名表**：
   - 打开别名表：https://docs.google.com/spreadsheets/d/1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc
   - 点击右上角"共享"按钮
   - 添加服务账号邮箱
   - 选择"查看者"权限
   - 点击"发送"

### 错误 2：工作表名称错误（400 Bad Request）

```
Unable to parse range: RawData!A1:U
```

**原因**：工作表名称 `RawData` 不存在

**解决方案**：

#### 步骤 A：找到正确的工作表名称

运行诊断脚本（需要先设置环境变量）：

```bash
# 1. 设置环境变量
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account.json"

# 2. 运行诊断
python3 scripts/diagnose_sheets.py
```

诊断脚本会列出所有工作表名称。

#### 步骤 B：手动检查

1. 打开原始表：https://docs.google.com/spreadsheets/d/1wescUQe9rIVLNcKdqmSLpzlAw9BGXMZmkFvjEF296nM
2. 查看底部的工作表标签
3. 记下第一个工作表的名称（例如：`Sheet1`、`原始数据`、`Sunday Worship` 等）

#### 步骤 C：更新配置

编辑 `config/config.json`，修改 `source_sheet.range`：

```json
{
  "source_sheet": {
    "url": "https://docs.google.com/spreadsheets/d/1wescUQe9rIVLNcKdqmSLpzlAw9BGXMZmkFvjEF296nM/edit#gid=0",
    "range": "正确的工作表名称!A1:Z"  // ← 修改这里
  }
}
```

**常见工作表名称**：
- `Sheet1!A1:Z`
- `原始数据!A1:Z`
- `Sunday Worship!A1:Z`
- `All in One!A1:Z`

## 🔍 诊断步骤

### 1. 检查服务账号设置

```bash
# 检查环境变量
echo $GOOGLE_APPLICATION_CREDENTIALS

# 检查文件是否存在
ls -lh "$GOOGLE_APPLICATION_CREDENTIALS"

# 查看服务账号邮箱
cat "$GOOGLE_APPLICATION_CREDENTIALS" | python3 -m json.tool | grep client_email
```

### 2. 运行完整诊断

```bash
# 设置环境变量（如果还没设置）
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# 运行诊断脚本
python3 scripts/diagnose_sheets.py
```

诊断脚本会告诉你：
- ✅ 哪些表可以访问
- ❌ 哪些表没有权限
- 📋 每个表的工作表列表
- 💡 建议的配置

### 3. 验证权限

对于每个 Google Sheet，确认服务账号已添加：

| Sheet | URL | 需要权限 |
|-------|-----|---------|
| 原始表 | ...1wescUQe9rIVLNcKdqmSLpzlAw9BGXMZmkFvjEF296nM | 查看者 |
| 目标表 | ...1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc | 编辑者 |
| 别名表 | ...1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc | 查看者 |

## ✅ 完整修复步骤

### 步骤 1：设置环境变量

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account.json"
```

### 步骤 2：运行诊断

```bash
python3 scripts/diagnose_sheets.py
```

### 步骤 3：根据诊断结果修复

#### 如果显示权限错误：

1. 从诊断输出中找到服务账号邮箱
2. 在每个 Google Sheet 中添加该邮箱
3. 设置适当的权限

#### 如果显示工作表名称错误：

1. 从诊断输出中找到正确的工作表名称
2. 编辑 `config/config.json`
3. 更新 `source_sheet.range`

### 步骤 4：重新测试

```bash
./run_test.sh
```

## 📝 快速修复命令

```bash
# 一键诊断和修复

# 1. 设置环境变量
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/service-account.json"

# 2. 查看服务账号邮箱
echo "服务账号邮箱："
cat "$GOOGLE_APPLICATION_CREDENTIALS" | python3 -m json.tool | grep client_email

# 3. 运行诊断
python3 scripts/diagnose_sheets.py

# 4. 根据诊断结果修复后，重新测试
./run_test.sh
```

## ❓ 常见问题

### Q: 如何找到服务账号 JSON 文件？

A: 常见位置：
```bash
# 在当前目录
ls *.json

# 在下载目录
ls ~/Downloads/*.json

# 搜索整个用户目录
find ~ -name "*service*account*.json" 2>/dev/null | head -5
```

### Q: 服务账号邮箱在哪里？

A: 
```bash
cat service-account.json | python3 -m json.tool | grep client_email
```

输出类似：`"client_email": "xxx@xxx.iam.gserviceaccount.com"`

### Q: 如何确认工作表名称？

A: 
1. 打开 Google Sheet
2. 查看底部的标签页
3. 标签页上的文字就是工作表名称

### Q: range 的格式是什么？

A: 格式：`工作表名称!起始列起始行:结束列结束行`

示例：
- `Sheet1!A1:Z` - 从 A1 开始到 Z 列的所有行
- `原始数据!A1:U100` - A1 到 U100
- `All in One!A:Z` - 整个 A 到 Z 列

## 🎯 验证修复

修复后，运行以下命令验证：

```bash
# 1. 干跑测试（不写入）
./run_test.sh

# 2. 检查输出
cat logs/clean_preview.csv | head -20

# 3. 如果成功，查看完整报告
cat logs/validation_report_*.txt
```

成功的标志：
```
✅ 读取原始表成功：N 行
✅ 清洗成功行：M 行
⚠️  警告行：W 行
❌ 错误行：0 行
```

---

**需要帮助？** 运行 `python3 scripts/diagnose_sheets.py` 获取详细诊断信息。

