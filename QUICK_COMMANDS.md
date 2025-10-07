# 快速命令参考 🚀

## 📌 常用命令速查

### 🔍 查看服务状态
```bash
# 健康检查
curl https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app/health

# 获取统计信息
curl https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app/api/v1/stats

# 查看定时任务状态
gcloud scheduler jobs describe ministry-data-cleaning-scheduler \
  --location=us-central1 \
  --format="value(state,scheduleTime)"
```

### ▶️ 手动触发清洗
```bash
# 方法1: 通过API（dry-run）
curl -X POST "https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app/api/v1/clean" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# 方法2: 通过API（正式运行）
curl -X POST "https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app/api/v1/clean" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "force": true}'

# 方法3: 通过 Cloud Scheduler
gcloud scheduler jobs run ministry-data-cleaning-scheduler --location=us-central1
```

### ⏸️ 管理定时任务
```bash
# 暂停
gcloud scheduler jobs pause ministry-data-cleaning-scheduler --location=us-central1

# 恢复
gcloud scheduler jobs resume ministry-data-cleaning-scheduler --location=us-central1

# 查看详情
gcloud scheduler jobs describe ministry-data-cleaning-scheduler --location=us-central1
```

### 📋 查看日志
```bash
# Cloud Run 服务日志（最近10条）
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-cleaning" \
  --limit 10 \
  --format="table(timestamp,severity,textPayload)"

# 只看错误
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-cleaning AND severity>=ERROR" \
  --limit 10

# Cloud Scheduler 日志
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=ministry-data-cleaning-scheduler" \
  --limit 10
```

### 🔄 更新部署
```bash
# 1. 构建新镜像
gcloud builds submit --tag gcr.io/ai-for-god/ministry-data-cleaning .

# 2. 部署到 Cloud Run
gcloud run deploy ministry-data-cleaning \
  --image=gcr.io/ai-for-god/ministry-data-cleaning:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated
```

### 🧪 运行测试
```bash
# 测试所有 API 端点
./test_deployed_api.sh

# 测试变化检测
./test_change_detection.sh
```

### 🌐 Web 控制台
```bash
# Cloud Run
https://console.cloud.google.com/run/detail/us-central1/ministry-data-cleaning?project=ai-for-god

# Cloud Scheduler
https://console.cloud.google.com/cloudscheduler?project=ai-for-god

# 日志
https://console.cloud.google.com/logs?project=ai-for-god
```

### 🔑 环境变量
```bash
# 导出必要的环境变量
export GCP_PROJECT_ID="ai-for-god"
export GCP_REGION="us-central1"
export SCHEDULER_TOKEN="2aabb0d776fe8961a6c40e507a2ecd548a1e46947438328350a1494318b229dd"
export SERVICE_URL="https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app"
```

---

## 📞 重要 URL

| 名称 | URL |
|------|-----|
| 服务地址 | https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app |
| API 文档 | https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app/docs |
| 健康检查 | https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app/health |

## 🎯 API 端点速查

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/clean` | POST | 手动清洗 |
| `/api/v1/stats` | GET | 统计信息 |
| `/api/v1/preview` | GET | 预览数据 |
| `/api/v1/query` | POST | 查询数据 |
| `/trigger-cleaning` | POST | 定时触发（需认证）|
| `/mcp/tools` | GET | MCP 工具定义 |

---

**快速参考** | 更新时间: 2025-10-07

