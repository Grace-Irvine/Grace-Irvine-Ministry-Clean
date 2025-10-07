# 云部署快速开始 ⚡

5 分钟快速部署到 Google Cloud Run！

## 前提条件

- ✅ 已安装 [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- ✅ 已安装 [Docker](https://docs.docker.com/get-docker/)
- ✅ 已配置 `config/config.json`
- ✅ 已配置 `config/service-account.json`

## 快速部署（3 步）

### 1️⃣ 设置环境变量

```bash
# 设置项目 ID（替换为你的项目 ID）
export GCP_PROJECT_ID="your-project-id"

# 设置区域（可选，默认 us-central1）
export GCP_REGION="us-central1"

# 生成安全令牌
export SCHEDULER_TOKEN=$(openssl rand -hex 32)
echo "请保存此令牌: $SCHEDULER_TOKEN"
```

### 2️⃣ 部署到 Cloud Run

```bash
# 赋予执行权限
chmod +x deploy-cloud-run.sh

# 运行部署脚本
./deploy-cloud-run.sh
```

**等待 5-10 分钟完成部署。**

### 3️⃣ 设置定时任务

```bash
# 获取服务 URL（从部署脚本输出中复制）
export SERVICE_URL="https://ministry-data-cleaning-xxx.run.app"

# 赋予执行权限
chmod +x setup-cloud-scheduler.sh

# 运行设置脚本
./setup-cloud-scheduler.sh
```

## ✅ 验证部署

### 测试健康检查

```bash
curl $SERVICE_URL/health
```

**预期输出：**
```json
{"status":"healthy","timestamp":"2025-10-06T10:00:00Z","version":"1.0.0"}
```

### 查看 API 文档

在浏览器中打开：
```
https://your-service-url.run.app/docs
```

### 测试数据清洗（dry-run）

```bash
curl -X POST $SERVICE_URL/api/v1/clean \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

## 🎉 完成！

你的数据清洗服务现在会：
- ✅ 每小时自动运行
- ✅ 提供 REST API
- ✅ 支持 MCP (Model Context Protocol)

## 下一步

- 📖 [完整部署文档](CLOUD_DEPLOYMENT.md)
- 🤖 [MCP 集成指南](MCP_INTEGRATION.md)
- 🔍 [监控和日志](CLOUD_DEPLOYMENT.md#监控和日志)

## 常见问题

### Q: 如何查看日志？

```bash
gcloud logging tail \
  "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-cleaning"
```

### Q: 如何修改执行频率？

```bash
# 例如：改为每 30 分钟
gcloud scheduler jobs update http ministry-cleaning-hourly \
  --location=$GCP_REGION \
  --schedule='*/30 * * * *'
```

### Q: 成本是多少？

基本在 Google Cloud 免费额度内，**每月成本约 $0-1**。

详见 [成本估算](CLOUD_DEPLOYMENT.md#成本估算)。

### Q: 如何更新代码？

```bash
# 重新运行部署脚本即可
./deploy-cloud-run.sh
```

## 故障排除

如遇到问题，请查看：
- [完整部署文档](CLOUD_DEPLOYMENT.md)
- [故障排除章节](CLOUD_DEPLOYMENT.md#故障排除)
- [主 README](README.md)

