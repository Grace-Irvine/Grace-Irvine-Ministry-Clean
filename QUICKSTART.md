# 快速上手指南

## 🚀 5 分钟快速上手

### 步骤 1：环境准备

```bash
# 安装依赖
pip install -r requirements.txt
```

### 步骤 2：配置 Google 服务账号

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 Google Sheets API
4. 创建服务账号并下载 JSON 密钥
5. 设置环境变量：

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account.json"
```

### 步骤 3：共享 Google Sheets

将以下 Sheet 共享给服务账号邮箱（形如 `xxx@xxx.iam.gserviceaccount.com`）：

- **原始表**：只读（Viewer）权限
- **清洗表**：编辑（Editor）权限  
- **别名表**（可选）：只读（Viewer）权限

### 步骤 4：配置 config.json

编辑 `config/config.json`，填入你的 Google Sheets 信息：

```json
{
  "source_sheet": {
    "url": "https://docs.google.com/spreadsheets/d/你的原始表ID/edit",
    "range": "Sheet1!A1:Z"
  },
  "target_sheet": {
    "url": "https://docs.google.com/spreadsheets/d/你的清洗表ID/edit",
    "range": "CleanData!A1"
  },
  ...
}
```

### 步骤 5：运行测试

```bash
# 使用样例数据运行单元测试
pytest tests/test_cleaning.py -v
```

### 步骤 6：干跑模式（推荐先运行）

```bash
# 干跑模式：仅生成预览，不写回 Google Sheet
python scripts/clean_pipeline.py --config config/config.json --dry-run
```

检查生成的预览文件：
- `logs/clean_preview.csv`
- `logs/clean_preview.json`

### 步骤 7：正式运行

确认预览结果无误后，运行正式清洗：

```bash
python scripts/clean_pipeline.py --config config/config.json
```

## 📋 检查清单

运行前请确认：

- ✅ 已安装所有依赖
- ✅ 已配置 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量
- ✅ 服务账号有访问对应 Sheet 的权限
- ✅ `config.json` 中的 URL 和范围正确
- ✅ 已在干跑模式下测试过

## 🔍 验证结果

检查以下内容：

1. **控制台输出**：查看清洗摘要和错误/警告信息
2. **清洗表**：检查写入的数据是否正确
3. **日志文件**：`logs/validation_report_*.txt` 查看详细报告

## ❓ 遇到问题？

请参考 [README.md](README.md) 的「故障排除」章节，或查看详细的日志文件。

## 📚 更多信息

- 完整文档：[README.md](README.md)
- 任务说明：[prompts/README_prompt.md](prompts/README_prompt.md)
- 测试用例：[tests/test_cleaning.py](tests/test_cleaning.py)


