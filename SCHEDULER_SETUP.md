# Cloud Scheduler 定时任务配置完成 ✅

## 📋 配置摘要

**配置时间**: 2025-10-07  
**任务名称**: ministry-data-cleaning-scheduler  
**执行频率**: 每30分钟  
**时区**: Asia/Shanghai (北京时间)

## ⏰ 定时任务详情

### 基本信息
- **任务 ID**: `ministry-data-cleaning-scheduler`
- **Cron 表达式**: `*/30 * * * *` (每小时的第0分和第30分执行)
- **区域**: us-central1
- **状态**: ENABLED (已启用)

### 执行配置
- **目标 URL**: https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app/trigger-cleaning
- **HTTP 方法**: POST
- **认证**: Bearer Token
- **重试次数**: 3次
- **最小重试间隔**: 30秒
- **超时时间**: 180秒

### 执行时间示例
定时任务将在每天的以下时间执行（北京时间）：
- 00:00, 00:30, 01:00, 01:30, 02:00, 02:30, ...
- 每天共执行 **48 次**

## 🔄 工作流程

### 1. 定时触发
Cloud Scheduler 每30分钟自动触发 `/trigger-cleaning` 端点。

### 2. 变化检测
服务收到请求后：
1. 读取 Google Sheets 原始数据
2. 计算数据哈希值
3. 与上次运行的哈希值比较

### 3. 条件更新
- **有变化**: 执行完整的数据清洗和更新
  - 清洗数据
  - 应用别名映射
  - 校验数据质量
  - 写入清洗层 Google Sheet
  - 更新状态文件
  
- **无变化**: 跳过清洗，直接返回
  - 节省资源
  - 减少 API 调用
  - 避免不必要的写入

## ✅ 测试结果

### 手动触发测试
```bash
gcloud scheduler jobs run ministry-data-cleaning-scheduler --location=us-central1
```

### 测试场景 1: 首次运行（强制执行）
```json
{
  "success": true,
  "message": "清洗管线执行成功",
  "changed": true,
  "change_reason": "forced",
  "total_rows": 131,
  "success_rows": 131,
  "warning_rows": 0,
  "error_rows": 0
}
```

### 测试场景 2: 数据无变化
```json
{
  "success": true,
  "message": "数据未发生变化，无需更新",
  "changed": false,
  "change_reason": "no_change",
  "total_rows": 131,
  "success_rows": 131,
  "last_update_time": "2025-10-07T00:54:37.491598Z"
}
```

### 日志验证
```
2025-10-07T00:55:23.479842Z  POST /trigger-cleaning HTTP/1.1" 200 OK
2025-10-07T00:55:23.256762Z  读取原始数据: 总表!A1:Z
2025-10-07T00:55:23.256340Z  成功加载别名映射: 125 个别名, 79 个唯一人员
2025-10-07T00:55:22.407761Z  收到定时触发请求，启动清洗任务...
```

## 🛠️ 管理命令

### 查看任务状态
```bash
gcloud scheduler jobs describe ministry-data-cleaning-scheduler \
  --location=us-central1
```

### 手动触发任务
```bash
gcloud scheduler jobs run ministry-data-cleaning-scheduler \
  --location=us-central1
```

### 暂停定时任务
```bash
gcloud scheduler jobs pause ministry-data-cleaning-scheduler \
  --location=us-central1
```

### 恢复定时任务
```bash
gcloud scheduler jobs resume ministry-data-cleaning-scheduler \
  --location=us-central1
```

### 更新执行频率
```bash
# 改为每小时执行一次
gcloud scheduler jobs update http ministry-data-cleaning-scheduler \
  --location=us-central1 \
  --schedule="0 * * * *"

# 改为每15分钟执行一次
gcloud scheduler jobs update http ministry-data-cleaning-scheduler \
  --location=us-central1 \
  --schedule="*/15 * * * *"

# 改为每天凌晨3点执行
gcloud scheduler jobs update http ministry-data-cleaning-scheduler \
  --location=us-central1 \
  --schedule="0 3 * * *"
```

### 删除定时任务
```bash
gcloud scheduler jobs delete ministry-data-cleaning-scheduler \
  --location=us-central1
```

## 📊 监控和日志

### 查看定时任务日志
```bash
# 查看最近10次执行日志
gcloud logging read \
  "resource.type=cloud_scheduler_job AND resource.labels.job_id=ministry-data-cleaning-scheduler" \
  --limit 10 \
  --format="table(timestamp,severity,textPayload)"
```

### 查看 Cloud Run 服务日志
```bash
# 查看最近的服务日志
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-cleaning" \
  --limit 50 \
  --format="table(timestamp,severity,textPayload)"

# 只查看错误日志
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-cleaning AND severity>=ERROR" \
  --limit 20
```

### Web 控制台
- **Cloud Scheduler**: https://console.cloud.google.com/cloudscheduler?project=ai-for-god
- **Cloud Run 日志**: https://console.cloud.google.com/run/detail/us-central1/ministry-data-cleaning/logs?project=ai-for-god
- **Logs Explorer**: https://console.cloud.google.com/logs?project=ai-for-god

## 🔍 变化检测机制

### 状态文件
系统在 Cloud Run 容器的 `/app/logs/pipeline_state.json` 中维护状态：

```json
{
  "last_run": "2025-10-07T00:54:44.134072Z",
  "last_hash": "abc123...",
  "last_row_count": 131,
  "last_update_time": "2025-10-07T00:54:37.491598Z",
  "run_count": 5
}
```

### 哈希计算
使用 SHA-256 算法对整个 DataFrame 的 JSON 表示进行哈希，确保能检测到：
- 新增行
- 删除行
- 修改内容
- 列顺序变化

### 变化类型
- `first_run`: 首次运行
- `rows_added`: 新增行
- `rows_removed`: 删除行
- `rows_modified`: 内容修改
- `no_change`: 无变化
- `forced`: 强制执行

## 🎯 使用场景

### 场景 1: 正常运行
定时任务每30分钟自动检查数据，如有变化则更新。

### 场景 2: 手动更新
如果需要立即更新，可以通过 API 强制执行：

```bash
curl -X POST "https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app/api/v1/clean" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "force": true}'
```

### 场景 3: 紧急维护
暂停定时任务进行维护：

```bash
# 暂停
gcloud scheduler jobs pause ministry-data-cleaning-scheduler --location=us-central1

# 完成维护后恢复
gcloud scheduler jobs resume ministry-data-cleaning-scheduler --location=us-central1
```

## 💰 成本优化

### 变化检测的优势
- **减少不必要的处理**: 无变化时跳过清洗，节省计算资源
- **降低 API 调用**: 只在数据变化时写入 Google Sheets
- **优化响应时间**: 无变化时快速返回（< 1秒）

### 预估成本（每月）
假设每天执行 48 次，每月约 1,440 次：

1. **Cloud Scheduler**
   - 前3个任务免费
   - 本项目: $0.00 (免费范围内)

2. **Cloud Run**
   - 有变化时（假设10%）: ~144次 × 5秒 = 720秒
   - 无变化时（90%）: ~1,296次 × 1秒 = 1,296秒
   - 总计: ~2,016秒/月
   - 前180,000秒免费
   - 本项目: $0.00 (免费范围内)

3. **Google Sheets API**
   - 读取: 1,440次/月
   - 写入: ~144次/月（仅在有变化时）
   - 配额: 500次/100秒/用户
   - 本项目: $0.00 (免费)

**总成本**: $0.00/月 ✅

## 🚨 告警和通知

### 设置失败告警
可以配置 Cloud Monitoring 在任务失败时发送通知：

```bash
# 创建告警策略（需要在 GCP 控制台配置）
# 1. 访问 Cloud Monitoring
# 2. 创建告警策略
# 3. 条件: Cloud Scheduler Job 失败
# 4. 通知渠道: Email/SMS/Slack
```

### 推荐告警条件
- 连续3次执行失败
- 错误率超过10%
- 执行时间超过5分钟

## 📚 相关文档

- [变化检测模块](./scripts/change_detector.py)
- [API 应用](./app.py)
- [部署文档](./DEPLOYMENT_SUCCESS.md)
- [故障排查](./TROUBLESHOOTING.md)

## ✨ 完成状态

- ✅ Cloud Scheduler 已配置
- ✅ 每30分钟自动执行
- ✅ 变化检测功能正常
- ✅ 认证令牌已设置
- ✅ 日志监控正常
- ✅ 手动测试通过

---

**配置完成时间**: 2025-10-07T00:55:09Z  
**下次执行时间**: 2025-10-07T01:00:00Z  
**状态**: ✅ 运行正常

