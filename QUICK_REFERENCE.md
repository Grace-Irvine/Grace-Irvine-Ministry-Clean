# 快速参考卡 🚀

一页纸速查常用命令和 API 端点。

## 📦 部署命令

### 初次部署

```bash
# 设置环境变量
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export SCHEDULER_TOKEN=$(openssl rand -hex 32)

# 部署到 Cloud Run
./deploy-cloud-run.sh

# 设置定时任务
export SERVICE_URL="https://your-service.run.app"
./setup-cloud-scheduler.sh
```

### 更新部署

```bash
# 重新部署
./deploy-cloud-run.sh

# 或仅更新代码
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/ministry-data-cleaning
gcloud run deploy ministry-data-cleaning \
  --image=gcr.io/$GCP_PROJECT_ID/ministry-data-cleaning \
  --region=$GCP_REGION
```

---

## 🔧 管理命令

### Cloud Run

```bash
# 查看服务详情
gcloud run services describe ministry-data-cleaning --region=$GCP_REGION

# 查看日志（实时）
gcloud logging tail \
  "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-cleaning"

# 查看最近日志
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-cleaning" \
  --limit 50

# 更新环境变量
gcloud run services update ministry-data-cleaning \
  --region=$GCP_REGION \
  --set-env-vars="KEY=VALUE"

# 更新资源配置
gcloud run services update ministry-data-cleaning \
  --region=$GCP_REGION \
  --memory=2Gi \
  --cpu=2
```

### Cloud Scheduler

```bash
# 查看任务详情
gcloud scheduler jobs describe ministry-cleaning-hourly --location=$GCP_REGION

# 手动触发任务
gcloud scheduler jobs run ministry-cleaning-hourly --location=$GCP_REGION

# 修改执行频率
gcloud scheduler jobs update http ministry-cleaning-hourly \
  --location=$GCP_REGION \
  --schedule='*/30 * * * *'  # 每 30 分钟

# 暂停/恢复任务
gcloud scheduler jobs pause ministry-cleaning-hourly --location=$GCP_REGION
gcloud scheduler jobs resume ministry-cleaning-hourly --location=$GCP_REGION

# 查看执行历史
gcloud logging read \
  "resource.type=cloud_scheduler_job AND resource.labels.job_id=ministry-cleaning-hourly" \
  --limit 10
```

---

## 🌐 API 端点

**基础 URL**: `https://your-service.run.app`

### 健康检查

```bash
curl $SERVICE_URL/health
```

### 查看 API 文档

```bash
# 在浏览器中打开
open $SERVICE_URL/docs
```

### 触发数据清洗

```bash
# 测试模式（不写入 Sheets）
curl -X POST $SERVICE_URL/api/v1/clean \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# 正式运行（写入 Sheets）
curl -X POST $SERVICE_URL/api/v1/clean \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

### 查询数据

```bash
# 查询所有数据（限制 10 条）
curl -X POST $SERVICE_URL/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'

# 按日期范围查询
curl -X POST $SERVICE_URL/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": "2025-01-01",
    "date_to": "2025-12-31",
    "limit": 50
  }'

# 按讲员查询
curl -X POST $SERVICE_URL/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "preacher": "张牧师",
    "limit": 20
  }'
```

### 获取统计信息

```bash
curl $SERVICE_URL/api/v1/stats
```

### 获取预览数据

```bash
curl $SERVICE_URL/api/v1/preview
```

### 获取 MCP 工具定义

```bash
curl $SERVICE_URL/mcp/tools
```

---

## 🐍 Python 客户端示例

```python
import requests

BASE_URL = "https://your-service.run.app"

# 查询数据
def query_data(date_from=None, preacher=None, limit=100):
    response = requests.post(
        f"{BASE_URL}/api/v1/query",
        json={
            "date_from": date_from,
            "preacher": preacher,
            "limit": limit
        }
    )
    return response.json()

# 获取统计
def get_stats():
    response = requests.get(f"{BASE_URL}/api/v1/stats")
    return response.json()

# 触发清洗
def trigger_clean(dry_run=True):
    response = requests.post(
        f"{BASE_URL}/api/v1/clean",
        json={"dry_run": dry_run}
    )
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 查询数据
    result = query_data(date_from="2025-01-01", preacher="张牧师")
    print(f"找到 {result['count']} 条记录")
    
    # 获取统计
    stats = get_stats()
    print(f"总记录数: {stats['stats']['total_records']}")
    
    # 测试清洗
    clean_result = trigger_clean(dry_run=True)
    print(f"清洗结果: {clean_result['message']}")
```

---

## 📅 Cron 表达式参考

| 描述 | Cron 表达式 | 示例 |
|------|-------------|------|
| 每小时 | `0 * * * *` | 每小时整点执行 |
| 每 30 分钟 | `*/30 * * * *` | :00 和 :30 执行 |
| 每 15 分钟 | `*/15 * * * *` | :00, :15, :30, :45 执行 |
| 每天 2 AM | `0 2 * * *` | 每天凌晨 2:00 执行 |
| 每天 9 AM | `0 9 * * *` | 每天上午 9:00 执行 |
| 每周一 9 AM | `0 9 * * 1` | 每周一上午 9:00 执行 |
| 每月 1 号 | `0 0 1 * *` | 每月 1 号午夜执行 |
| 工作日 9 AM | `0 9 * * 1-5` | 周一到周五 9:00 执行 |

---

## 🔍 常见问题快速解决

### 查看部署状态

```bash
gcloud run services describe ministry-data-cleaning \
  --region=$GCP_REGION \
  --format="value(status.url,status.conditions)"
```

### 测试服务可用性

```bash
curl -v $SERVICE_URL/health
```

### 查看最新错误日志

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-cleaning AND severity>=ERROR" \
  --limit 20
```

### 重启服务

```bash
gcloud run services update ministry-data-cleaning \
  --region=$GCP_REGION \
  --no-traffic  # 不会影响流量

gcloud run services update ministry-data-cleaning \
  --region=$GCP_REGION
```

### 查看资源使用情况

```bash
# 在 Cloud Console 查看
open "https://console.cloud.google.com/run/detail/$GCP_REGION/ministry-data-cleaning/metrics?project=$GCP_PROJECT_ID"
```

---

## 🗑️ 清理资源

```bash
# 删除 Cloud Run 服务
gcloud run services delete ministry-data-cleaning --region=$GCP_REGION --quiet

# 删除 Cloud Scheduler 任务
gcloud scheduler jobs delete ministry-cleaning-hourly --location=$GCP_REGION --quiet

# 删除容器镜像
gcloud container images delete gcr.io/$GCP_PROJECT_ID/ministry-data-cleaning --quiet

# 删除 Secret
gcloud secrets delete ministry-service-account --quiet
```

---

## 📞 获取帮助

| 问题类型 | 查看文档 |
|---------|---------|
| 快速部署 | [CLOUD_QUICKSTART.md](CLOUD_QUICKSTART.md) |
| 完整部署 | [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) |
| API 使用 | [MCP_INTEGRATION.md](MCP_INTEGRATION.md) |
| 本地调试 | [QUICK_DEBUG_GUIDE.md](QUICK_DEBUG_GUIDE.md) |
| 故障排除 | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |

---

## 💡 提示

- 💾 **保存环境变量**：将常用变量保存到 `~/.zshrc` 或 `~/.bashrc`
- 📝 **记录令牌**：将 `SCHEDULER_TOKEN` 保存到安全的地方
- 🔄 **定期更新**：定期运行 `./deploy-cloud-run.sh` 更新代码
- 📊 **监控日志**：设置告警以及时发现问题
- 💰 **控制成本**：定期检查 Cloud Console 的计费报告

---

**快速访问文档**：
- 📖 [README.md](README.md) - 主文档
- ⚡ [CLOUD_QUICKSTART.md](CLOUD_QUICKSTART.md) - 快速开始
- 🤖 [MCP_INTEGRATION.md](MCP_INTEGRATION.md) - AI 集成

