# Google Cloud 部署指南

本文档详细介绍如何将教会主日事工数据清洗管线部署到 Google Cloud Run，并设置定时任务。

## 📋 目录

- [前提条件](#前提条件)
- [架构概览](#架构概览)
- [部署步骤](#部署步骤)
- [配置定时任务](#配置定时任务)
- [测试部署](#测试部署)
- [监控和日志](#监控和日志)
- [成本估算](#成本估算)
- [故障排除](#故障排除)

## 前提条件

### 1. 必需的工具

- **Google Cloud SDK**：[安装指南](https://cloud.google.com/sdk/docs/install)
- **Docker**：[安装指南](https://docs.docker.com/get-docker/)
- **Git**：用于克隆代码库

### 2. Google Cloud 项目

1. 创建或选择一个 Google Cloud 项目
2. 启用计费（Cloud Run 有免费额度）
3. 记录项目 ID

### 3. Google Sheets 配置

确保已完成以下配置：

1. ✅ 创建服务账号并下载 JSON 密钥文件
2. ✅ 将服务账号邮箱添加到相关 Google Sheets
3. ✅ 配置 `config/config.json`
4. ✅ 将服务账号密钥保存到 `config/service-account.json`

详见主 [README.md](../README.md) 的配置部分。

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     Google Cloud Platform                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────┐         ┌──────────────────────┐     │
│  │ Cloud Scheduler   │────────>│   Cloud Run          │     │
│  │                   │  HTTP   │   (FastAPI App)      │     │
│  │ • 每小时触发      │ POST    │   • 数据清洗 API     │     │
│  │ • Bearer Token    │         │   • MCP 兼容         │     │
│  └───────────────────┘         └──────────────────────┘     │
│                                          │                    │
│                                          │ API               │
│                                          ▼                    │
│                                 ┌─────────────────┐          │
│                                 │  Secret Manager │          │
│                                 │  • 服务账号密钥 │          │
│                                 └─────────────────┘          │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                                          │
                                          │ Google Sheets API
                                          ▼
                               ┌──────────────────────┐
                               │   Google Sheets      │
                               │   • 原始数据表       │
                               │   • 清洗数据表       │
                               │   • 别名表           │
                               └──────────────────────┘
```

## 部署步骤

### 步骤 1：准备项目

```bash
# 克隆项目（如果还未克隆）
cd /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean

# 确保所有配置文件就绪
ls -la config/
# 应该看到：
# - config.json
# - service-account.json
```

### 步骤 2：设置环境变量

```bash
# 设置 Google Cloud 项目 ID
export GCP_PROJECT_ID="your-project-id"

# 设置部署区域（可选，默认 us-central1）
export GCP_REGION="us-central1"

# 生成并设置调度器令牌（用于安全认证）
export SCHEDULER_TOKEN=$(openssl rand -hex 32)
echo "请保存此令牌: $SCHEDULER_TOKEN"
```

### 步骤 3：执行部署脚本

```bash
# 赋予脚本执行权限
chmod +x deploy-cloud-run.sh

# 执行部署
./deploy-cloud-run.sh
```

**部署脚本会自动完成以下操作：**

1. ✅ 验证 gcloud 和 docker 安装
2. ✅ 设置 GCP 项目
3. ✅ 启用必要的 API（Cloud Build, Cloud Run, Secret Manager）
4. ✅ 创建服务账号（如果不存在）
5. ✅ 上传服务账号密钥到 Secret Manager
6. ✅ 构建 Docker 镜像
7. ✅ 部署到 Cloud Run
8. ✅ 输出服务 URL

**预计时间：** 5-10 分钟

### 步骤 4：记录服务信息

部署完成后，记录以下信息：

```bash
# 服务 URL（会在部署脚本输出中显示）
export SERVICE_URL="https://ministry-data-cleaning-xxx-uc.a.run.app"

# 调度器令牌（之前生成的）
export SCHEDULER_TOKEN="your-scheduler-token-here"
```

## 配置定时任务

### 步骤 1：设置 Cloud Scheduler

```bash
# 赋予脚本执行权限
chmod +x setup-cloud-scheduler.sh

# 确保环境变量已设置
echo "SERVICE_URL: $SERVICE_URL"
echo "SCHEDULER_TOKEN: ${SCHEDULER_TOKEN:0:10}..."

# 执行设置脚本
./setup-cloud-scheduler.sh
```

**脚本会自动完成以下操作：**

1. ✅ 启用 Cloud Scheduler API
2. ✅ 创建定时任务（每小时运行一次）
3. ✅ 配置认证令牌
4. ✅ 执行一次测试运行

### 步骤 2：验证定时任务

```bash
# 查看任务详情
gcloud scheduler jobs describe ministry-cleaning-hourly \
  --location=$GCP_REGION

# 查看最近的执行历史
gcloud scheduler jobs list --location=$GCP_REGION
```

### 步骤 3：修改执行频率（可选）

默认配置为每小时运行一次（`0 * * * *`）。如需修改：

```bash
# 修改为每 30 分钟运行一次
gcloud scheduler jobs update http ministry-cleaning-hourly \
  --location=$GCP_REGION \
  --schedule='*/30 * * * *'

# 修改为每天凌晨 2 点运行
gcloud scheduler jobs update http ministry-cleaning-hourly \
  --location=$GCP_REGION \
  --schedule='0 2 * * *'
```

**常用 Cron 表达式：**

| 描述 | Cron 表达式 |
|------|-------------|
| 每小时 | `0 * * * *` |
| 每 30 分钟 | `*/30 * * * *` |
| 每天 2 AM | `0 2 * * *` |
| 每周一 9 AM | `0 9 * * 1` |
| 每月 1 号 | `0 0 1 * *` |

## 测试部署

### 1. 健康检查

```bash
curl $SERVICE_URL/health
```

**预期输出：**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-06T10:00:00Z",
  "version": "1.0.0"
}
```

### 2. 查看 API 文档

在浏览器中访问：
```
https://your-service-url.run.app/docs
```

这会显示 FastAPI 自动生成的交互式 API 文档（Swagger UI）。

### 3. 手动触发清洗（测试模式）

```bash
curl -X POST $SERVICE_URL/api/v1/clean \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

**预期输出：**
```json
{
  "success": true,
  "message": "清洗管线执行成功",
  "total_rows": 100,
  "success_rows": 95,
  "warning_rows": 3,
  "error_rows": 2,
  "timestamp": "2025-10-06T10:00:00Z",
  "preview_available": true
}
```

### 4. 查询数据

```bash
curl -X POST $SERVICE_URL/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": "2025-01-01",
    "limit": 5
  }'
```

### 5. 获取统计信息

```bash
curl $SERVICE_URL/api/v1/stats
```

## 监控和日志

### 查看 Cloud Run 日志

```bash
# 查看最近的日志
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-cleaning" \
  --limit 50 \
  --format json

# 实时查看日志
gcloud logging tail \
  "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-cleaning"
```

### 查看 Cloud Scheduler 日志

```bash
# 查看调度器执行日志
gcloud logging read \
  "resource.type=cloud_scheduler_job AND resource.labels.job_id=ministry-cleaning-hourly" \
  --limit 10
```

### Cloud Console 监控

访问 [Google Cloud Console](https://console.cloud.google.com/)：

1. **Cloud Run**：查看服务状态、请求量、延迟等
   - Navigation Menu → Cloud Run → ministry-data-cleaning
   
2. **Cloud Scheduler**：查看任务执行历史
   - Navigation Menu → Cloud Scheduler → ministry-cleaning-hourly
   
3. **Logs Explorer**：高级日志查询和过滤
   - Navigation Menu → Logging → Logs Explorer

### 设置告警（可选）

```bash
# 创建告警策略：当错误率超过 5% 时发送通知
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Ministry Cleaning Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=300s
```

## 成本估算

### Cloud Run 定价

Cloud Run 提供慷慨的免费额度：

- **免费额度（每月）：**
  - 2 百万次请求
  - 360,000 GB-秒内存
  - 180,000 vCPU-秒

- **付费定价（超出免费额度后）：**
  - 请求：$0.40 / 百万次
  - CPU：$0.00002400 / vCPU-秒
  - 内存：$0.00000250 / GB-秒

### Cloud Scheduler 定价

- **免费额度：** 每月 3 个任务
- **付费定价：** $0.10 / 任务 / 月（第 4 个任务开始）

### 预估成本（每月）

**假设：**
- 每小时运行一次清洗任务（720 次/月）
- 每次运行约 30 秒
- 使用 1 GB 内存，1 vCPU

**计算：**
```
请求费用：720 / 2,000,000 × $0.40 = $0.00
CPU 费用：720 × 30 × 1 / 1,000,000 × $24 = $0.52
内存费用：720 × 30 × 1 / 1,000,000 × $2.50 = $0.05
调度器费用：$0.00 (在免费额度内)

总计：约 $0.57 / 月
```

**✅ 结论：基本在免费额度内，成本几乎为零！**

## 故障排除

### 问题 1：部署失败 - 权限不足

**错误信息：**
```
ERROR: (gcloud.run.deploy) PERMISSION_DENIED
```

**解决方案：**
```bash
# 确保你有必要的 IAM 角色
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/iam.serviceAccountUser"
```

### 问题 2：服务无法访问 Google Sheets

**错误信息：**
```
HttpError 403: Permission denied
```

**解决方案：**

1. 确认服务账号邮箱添加到了 Google Sheets：
   ```bash
   # 查看服务账号邮箱
   gcloud iam service-accounts list
   ```

2. 在 Google Sheets 中，点击"共享"，添加服务账号邮箱

3. 验证 Secret Manager 中的密钥：
   ```bash
   gcloud secrets versions access latest \
     --secret="ministry-service-account"
   ```

### 问题 3：Cloud Scheduler 任务失败

**错误信息：**
```
401 Unauthorized
```

**解决方案：**

检查环境变量是否正确设置：

```bash
# 查看 Cloud Run 服务的环境变量
gcloud run services describe ministry-data-cleaning \
  --region=$GCP_REGION \
  --format="value(spec.template.spec.containers[0].env)"

# 更新 SCHEDULER_TOKEN
gcloud run services update ministry-data-cleaning \
  --region=$GCP_REGION \
  --set-env-vars="SCHEDULER_TOKEN=your-new-token"

# 同时更新 Cloud Scheduler
gcloud scheduler jobs update http ministry-cleaning-hourly \
  --location=$GCP_REGION \
  --headers="Authorization=Bearer your-new-token"
```

### 问题 4：容器构建失败

**错误信息：**
```
ERROR: failed to build: ...
```

**解决方案：**

```bash
# 本地测试 Dockerfile
docker build -t ministry-cleaning-test .

# 运行容器测试
docker run -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  ministry-cleaning-test

# 在另一个终端测试
curl http://localhost:8080/health
```

### 问题 5：内存不足

**错误信息：**
```
Container failed to allocate memory
```

**解决方案：**

增加内存配置：

```bash
gcloud run services update ministry-data-cleaning \
  --region=$GCP_REGION \
  --memory=2Gi
```

## 更新部署

### 方式 1：重新运行部署脚本

```bash
./deploy-cloud-run.sh
```

### 方式 2：仅更新代码

```bash
# 构建新镜像
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/ministry-data-cleaning

# 部署新版本
gcloud run deploy ministry-data-cleaning \
  --image=gcr.io/$GCP_PROJECT_ID/ministry-data-cleaning \
  --region=$GCP_REGION
```

### 方式 3：更新配置

```bash
# 更新环境变量
gcloud run services update ministry-data-cleaning \
  --region=$GCP_REGION \
  --set-env-vars="KEY=VALUE"

# 更新资源限制
gcloud run services update ministry-data-cleaning \
  --region=$GCP_REGION \
  --memory=2Gi \
  --cpu=2
```

## 清理资源

如需删除所有部署的资源：

```bash
# 删除 Cloud Run 服务
gcloud run services delete ministry-data-cleaning \
  --region=$GCP_REGION \
  --quiet

# 删除 Cloud Scheduler 任务
gcloud scheduler jobs delete ministry-cleaning-hourly \
  --location=$GCP_REGION \
  --quiet

# 删除容器镜像
gcloud container images delete \
  gcr.io/$GCP_PROJECT_ID/ministry-data-cleaning \
  --quiet

# 删除 Secret
gcloud secrets delete ministry-service-account --quiet

# 删除服务账号（可选）
gcloud iam service-accounts delete \
  ministry-cleaning-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com \
  --quiet
```

## 下一步

- 📖 阅读 [MCP_INTEGRATION.md](MCP_INTEGRATION.md) 了解如何与 AI 助手集成
- 🔒 配置 API 认证和速率限制
- 📊 设置自定义监控和告警
- 🌍 添加 CDN 以提升全球访问速度

## 支持

如有问题或建议，请：
1. 查看主 [README.md](../README.md)
2. 查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. 提交 GitHub Issue

