# 设置和运行指南 🚀

## 📋 配置检查清单

✅ **源表已配置**：`1wescUQe9rIVLNcKdqmSLpzlAw9BGXMZmkFvjEF296nM`  
✅ **目标表已配置**：`1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc`  
✅ **别名表已配置**：`PeopleAliases!A1:C`  
⏳ **待完成**：设置 Google 服务账号凭证

## 🔑 步骤 1：设置 Google 服务账号凭证

### 选项 A：如果你已有服务账号 JSON 文件

```bash
# 设置环境变量（替换为你的文件路径）
export GOOGLE_APPLICATION_CREDENTIALS="/完整路径/你的服务账号文件.json"

# 或者，如果文件在项目目录下：
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/你的服务账号文件.json"
```

### 选项 B：如果还没有服务账号

1. **创建服务账号**：
   - 访问 [Google Cloud Console](https://console.cloud.google.com/)
   - 创建新项目或选择现有项目
   - 启用 Google Sheets API
   - 创建服务账号并下载 JSON 密钥

2. **配置权限**：
   打开你的 Google Sheets，点击"共享"，添加服务账号邮箱（形如 `xxx@xxx.iam.gserviceaccount.com`）：
   
   | Sheet | 权限 |
   |-------|------|
   | 原始表（源表） | 查看者（Viewer） |
   | 清洗表（目标表） | 编辑者（Editor） |
   | 别名表 | 查看者（Viewer） |

3. **设置环境变量**：
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account.json"
   ```

## 🧪 步骤 2：运行干跑测试

使用干跑模式测试（不会写入 Google Sheet）：

### 方法 1：使用测试脚本（推荐）

```bash
./run_test.sh
```

这个脚本会：
- ✅ 检查环境变量
- ✅ 运行干跑模式
- ✅ 生成预览文件
- ✅ 显示详细报告

### 方法 2：手动运行

```bash
python3 scripts/clean_pipeline.py --config config/config.json --dry-run
```

## 📊 步骤 3：检查结果

干跑完成后，检查生成的文件：

```bash
# 查看 CSV 预览
open logs/clean_preview.csv

# 查看校验报告
cat logs/validation_report_*.txt

# 查看 JSON 格式
cat logs/clean_preview.json | python3 -m json.tool | head -50
```

### 检查要点

| 项目 | 检查内容 | 预期结果 |
|-----|---------|---------|
| ✅ 日期格式 | service_date 列 | YYYY-MM-DD |
| ✅ 人员 ID | preacher_id, worship_lead_id 等 | 正确映射到别名 |
| ✅ 显示名称 | preacher_name 等 | 统一的显示名 |
| ✅ 歌曲拆分 | songs 列 | JSON 数组格式 |
| ✅ 空值处理 | 各列 | 空值正确处理 |

## ✅ 步骤 4：正式运行

确认预览结果无误后，运行正式清洗：

### 方法 1：使用便捷脚本

```bash
./run_pipeline.sh
```

### 方法 2：手动运行

```bash
python3 scripts/clean_pipeline.py --config config/config.json
```

## 📝 步骤 5：验证写入结果

1. 打开目标 Google Sheet
2. 检查 `CleanData` 工作表
3. 验证数据是否正确写入

## 🔍 故障排除

### 问题 1：找不到服务账号文件

```bash
❌ 错误: 服务账号文件不存在
```

**解决**：
- 检查文件路径是否正确
- 确认文件名拼写无误
- 使用绝对路径

### 问题 2：权限不足

```bash
❌ HttpError 403: Permission denied
```

**解决**：
1. 在 Google Sheet 中添加服务账号为协作者
2. 确认权限设置：
   - 原始表：Viewer
   - 目标表：Editor
   - 别名表：Viewer

### 问题 3：找不到工作表

```bash
❌ 错误: 指定范围没有数据
```

**解决**：
- 检查 `config.json` 中的 `range` 配置
- 确认工作表名称正确（如 `RawData!A1:U`）
- 确认范围包含数据

### 问题 4：读取别名表失败

```bash
⚠️ 警告: 未加载别名映射
```

**解决**：
1. 检查别名表 URL 是否正确
2. 确认工作表名称为 `PeopleAliases`
3. 确认别名表有三列：alias, person_id, display_name
4. 确认服务账号有访问权限

## 🎯 快速参考

### 环境变量设置（每次打开新终端需要）

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

### 测试流程

```bash
# 1. 干跑测试
./run_test.sh

# 2. 检查结果
open logs/clean_preview.csv

# 3. 正式运行
./run_pipeline.sh
```

### 重新运行

如果需要重新运行：

```bash
# 清空日志目录
rm logs/*.csv logs/*.json logs/*.txt

# 重新运行干跑
./run_test.sh
```

## 📞 获取帮助

```bash
# 查看帮助
python3 scripts/clean_pipeline.py --help

# 查看配置
cat config/config.json

# 检查环境
echo $GOOGLE_APPLICATION_CREDENTIALS
ls -lh "$GOOGLE_APPLICATION_CREDENTIALS"
```

## ✨ 成功标志

运行成功后，你会看到：

```
============================================================
数据校验报告
============================================================
总行数: 131
成功行数: 130
警告行数: 1
错误行数: 0
总问题数: 1

✅ 读取原始表成功：131 行
✅ 清洗成功行：130 行
⚠️  警告行：1 行
❌ 错误行：0 行
✅ 目标表写入成功：130 行
============================================================
```

---

**当前状态**：⏳ 等待设置 Google 服务账号凭证  
**下一步**：设置环境变量后运行 `./run_test.sh`

