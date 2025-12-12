# 每周事工预览定时器服务

这个服务通过 Cloud Scheduler 定时触发，调用 MCP Server 生成每周事工预览并自动发送邮件。

## 📝 配置文件

敏感信息（SMTP 密码、邮箱地址、令牌等）保存在 `secrets.env` 文件中，该文件**不会被提交到 Git**。

**快速开始：**
```bash
cd mcp/example
cp secrets.env.example secrets.env
nano secrets.env  # 填入必需信息
chmod 600 secrets.env  # 设置文件权限
./setup-scheduler.sh  # 自动部署
```

详细配置说明请参考 [README-SECRETS.md](README-SECRETS.md)

## 功能特性

- ✅ 定时触发：通过 Cloud Scheduler 每周一早上9点自动触发
- ✅ 自动生成预览：调用 MCP Server 的 `generate_weekly_preview` 工具
- ✅ 邮件发送：自动将预览内容发送到指定邮箱
- ✅ 多种格式支持：支持 text、markdown、html 格式
- ✅ 健康检查：提供健康检查端点

### 预览内容包括

预览会自动包含以下信息：

**证道信息：**
- 📖 讲员
- 📖 读经
- 📖 题目
- 📖 系列
- 📖 经文

**同工安排：**
- 🎵 敬拜团队（敬拜带领、敬拜同工、司琴）
- 📺 媒体团队（音控、导播/摄影、ProPresenter播放、ProPresenter更新、视频剪辑）
- 👶 儿童事工（周五老师、周日助教）
- 🤝 外展联络（新人接待1、新人接待2）

## 架构

```
Cloud Scheduler (每周一9:00)
    ↓
Weekly Preview Scheduler (Cloud Run)
    ↓
MCP Server (Cloud Run) - generate_weekly_preview
    ↓
Email (SMTP)
```

## 环境变量配置

### 必需的环境变量

以下变量已预设默认值，如果使用默认值则无需设置：

```bash
# MCP Server 配置（已预设默认值）
# MCP_SERVER_URL=https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app  # 默认值
# MCP_BEARER_TOKEN=db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30  # 默认值

# SMTP 邮件配置（已预设默认发件人）
SMTP_SERVER=smtp.gmail.com  # 默认值
SMTP_PORT=587  # 默认值
SMTP_USER=jonathanjing@graceirvine.org  # 默认值
SMTP_PASSWORD=your-app-password  # 必需：Gmail 应用专用密码
EMAIL_FROM=jonathanjing@graceirvine.org  # 默认值
EMAIL_TO=recipient1@example.com,recipient2@example.com  # 必需：收件人地址
EMAIL_CC=cc@example.com  # 可选

# Cloud Scheduler 认证
SCHEDULER_TOKEN=your-secure-random-token  # 必需：安全的随机令牌
```

**预设默认配置**：
- ✅ MCP Server URL: `https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app`
- ✅ MCP Bearer Token: 已预设
- ✅ 发件人邮箱: `jonathanjing@graceirvine.org`
- ✅ SMTP 服务器: `smtp.gmail.com` (Gmail)

**必需设置的变量**：
- `SMTP_PASSWORD` - Gmail 应用专用密码
- `EMAIL_TO` - 收件人邮箱地址
- `SCHEDULER_TOKEN` - Scheduler 认证令牌

### 快速设置（推荐）

使用 `setup-scheduler.sh` 脚本进行快速设置：

```bash
cd mcp/example
./setup-scheduler.sh
```

该脚本会：
1. 自动创建敏感信息配置文件 `secrets.env`（如果不存在）
2. 使用预设的 MCP 配置和发件人邮箱
3. 引导您填入必需的配置（SMTP_PASSWORD, EMAIL_TO, EMAIL_CC, SCHEDULER_TOKEN）
4. 自动设置文件权限（仅所有者可读写）
5. 自动部署到 Cloud Run 并创建 Cloud Scheduler 任务

**关于配置文件：**
- 敏感信息保存在 `secrets.env` 文件中（不会被提交到 Git）
- 详细配置说明请参考 [README-SECRETS.md](README-SECRETS.md)

### Gmail 配置说明

如果使用 Gmail，需要：

1. 启用两步验证
2. 生成应用专用密码：
   - 访问 [Google 账号设置](https://myaccount.google.com/apppasswords)
   - 生成应用专用密码
   - 使用生成的16位密码作为 `SMTP_PASSWORD`

### 可选的环境变量

```bash
# 日期格式（如果需要在特定日期生成预览）
DATE=2025-01-19  # 格式：YYYY-MM-DD，默认为下一个周日

# 输出格式（text, markdown, html）
FORMAT=html  # 默认为 text
```

## 部署步骤

### 1. 准备环境变量

创建 `.env` 文件或使用 Cloud Build 的替换变量：

```bash
_MCP_SERVER_URL=https://your-mcp-server-url.run.app
_MCP_BEARER_TOKEN=your-token
_SMTP_SERVER=smtp.gmail.com
_SMTP_PORT=587
_SMTP_USER=your-email@gmail.com
_SMTP_PASSWORD=your-app-password
_EMAIL_FROM=your-email@gmail.com
_EMAIL_TO=recipient@example.com
_SCHEDULER_TOKEN=generate-a-secure-random-token
```

### 2. 快速部署（推荐）

使用快速设置脚本：

```bash
cd mcp/example
./setup-scheduler.sh
```

### 3. 手动构建和部署

#### 方式 1：使用 Cloud Build

```bash
# 设置项目 ID
export PROJECT_ID=your-project-id

# 提交并触发构建
gcloud builds submit --config=mcp/example/cloudbuild.yaml \
  --substitutions=_MCP_SERVER_URL=...,_MCP_BEARER_TOKEN=...,_SMTP_SERVER=...,...
```

#### 方式 2：手动部署

```bash
# 1. 构建 Docker 镜像
cd /path/to/Grace-Irvine-Ministry-Clean
docker build -t weekly-preview-scheduler -f mcp/example/Dockerfile .

# 2. 标记并推送到 GCR
docker tag weekly-preview-scheduler gcr.io/$PROJECT_ID/weekly-preview-scheduler:latest
docker push gcr.io/$PROJECT_ID/weekly-preview-scheduler:latest

# 3. 部署到 Cloud Run
gcloud run deploy weekly-preview-scheduler \
  --image gcr.io/$PROJECT_ID/weekly-preview-scheduler:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 1 \
  --set-env-vars MCP_SERVER_URL=$MCP_SERVER_URL,MCP_BEARER_TOKEN=$MCP_BEARER_TOKEN,...
```

### 3. 创建 Cloud Scheduler 任务

```bash
# 获取服务 URL
SERVICE_URL=$(gcloud run services describe weekly-preview-scheduler \
  --region us-central1 \
  --format 'value(status.url)')

# 创建定时任务（每周一早上9点，太平洋时间）
gcloud scheduler jobs create http weekly-preview-job \
  --location=us-central1 \
  --schedule="0 9 * * 1" \
  --uri="$SERVICE_URL/trigger" \
  --http-method=POST \
  --headers="Authorization=Bearer $SCHEDULER_TOKEN" \
  --time-zone="America/Los_Angeles"
```

**注意**：`--schedule="0 9 * * 1"` 表示：
- `0` - 分钟（0分）
- `9` - 小时（9点）
- `*` - 每天
- `*` - 每月
- `1` - 周一（0=周日，1=周一，...）

### 4. 使用配置文件部署

使用敏感信息配置文件（推荐）：

```bash
# 1. 复制配置示例文件
cd mcp/example
cp secrets.env.example secrets.env

# 2. 编辑配置文件，填入必需信息
nano secrets.env

# 3. 设置文件权限（仅所有者可读写）
chmod 600 secrets.env

# 4. 加载配置并部署
source load-secrets.sh
./deploy.sh
```

**配置项说明：**
- `SMTP_PASSWORD` - Gmail 应用专用密码（必需）
- `EMAIL_TO` - 收件人邮箱地址（必需）
- `EMAIL_CC` - 抄送邮箱地址（可选）
- `SCHEDULER_TOKEN` - Scheduler 认证令牌（必需，可运行 `openssl rand -hex 32` 生成）

详细配置说明请参考 [README-SECRETS.md](README-SECRETS.md)

### 5. 测试任务

```bash
# 手动触发一次（用于测试）
gcloud scheduler jobs run weekly-preview-job --location=us-central1
```

或者直接调用 HTTP 端点：

```bash
curl -X POST "$SERVICE_URL/trigger" \
  -H "Authorization: Bearer $SCHEDULER_TOKEN" \
  -H "Content-Type: application/json"
```

## API 端点

### GET `/health`

健康检查端点

**响应示例：**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-13T09:00:00",
  "version": "1.0.0"
}
```

### POST `/trigger`

触发每周事工预览生成和邮件发送

**请求头：**
```
Authorization: Bearer <SCHEDULER_TOKEN>
Content-Type: application/json
```

**请求体（可选）：**
```json
{
  "date": "2025-01-19",  // 可选，默认为下一个周日
  "format": "html",       // text, markdown, html
  "year": "2025"          // 可选，指定年份
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "Weekly preview generated and email sent successfully",
  "date": "2025-01-19",
  "preview_length": 1234,
  "email_sent": true,
  "timestamp": "2025-01-13T09:00:00"
}
```

## 本地测试

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 设置环境变量

```bash
export MCP_SERVER_URL=https://your-mcp-server.run.app
export MCP_BEARER_TOKEN=your-token
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export EMAIL_FROM=your-email@gmail.com
export EMAIL_TO=recipient@example.com
export SCHEDULER_TOKEN=test-token
```

### 3. 运行服务

```bash
cd mcp/example
python weekly_preview_scheduler.py
```

### 4. 测试触发

```bash
curl -X POST "http://localhost:8080/trigger" \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{"format": "html"}'
```

## 故障排查

### 1. 邮件发送失败

- 检查 SMTP 配置是否正确
- 确认 Gmail 应用专用密码已正确设置
- 检查 `EMAIL_TO` 环境变量是否配置

### 2. MCP Server 调用失败

- 检查 `MCP_SERVER_URL` 是否正确
- 确认 `MCP_BEARER_TOKEN` 是否有效
- 查看 Cloud Run 日志：`gcloud logging read "resource.type=cloud_run_revision" --limit 50`

### 3. Cloud Scheduler 未触发

- 检查调度时间是否正确
- 确认时区设置（`--time-zone`）
- 查看 Scheduler 任务日志：`gcloud scheduler jobs describe weekly-preview-job --location=us-central1`

## 监控和日志

### 查看 Cloud Run 日志

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=weekly-preview-scheduler" --limit 50
```

### 查看 Cloud Scheduler 执行历史

```bash
gcloud scheduler jobs describe weekly-preview-job --location=us-central1
```

## 安全建议

1. **SCHEDULER_TOKEN**：使用强随机字符串，建议至少32个字符
2. **SMTP_PASSWORD**：使用应用专用密码，不要使用账户密码
3. **MCP_BEARER_TOKEN**：定期轮换，确保安全
4. **Cloud Run**：考虑使用 `--no-allow-unauthenticated` 并要求 IAM 认证

## 许可证

本项目采用 MIT 许可证。
