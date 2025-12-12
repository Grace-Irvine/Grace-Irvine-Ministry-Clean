#!/bin/bash
# 检查部署状态
# 使用方法: ./check-deployment.sh

echo "检查部署状态..."
echo ""

# 检查 Cloud Run 服务
echo "📦 Cloud Run 服务状态："
SERVICE_URL=$(gcloud run services describe weekly-preview-scheduler \
  --region us-central1 \
  --format 'value(status.url)' 2>/dev/null)

if [ -n "$SERVICE_URL" ]; then
  echo "✅ 服务已部署"
  echo "   服务 URL: $SERVICE_URL"
  echo ""
  
  # 检查健康状态
  HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health" 2>/dev/null || echo "000")
  if [ "$HEALTH" = "200" ]; then
    echo "✅ 服务健康检查通过"
  else
    echo "⚠️  服务健康检查失败 (HTTP $HEALTH)"
  fi
else
  echo "❌ 服务尚未部署"
fi

echo ""

# 检查 Cloud Scheduler 任务
echo "⏰ Cloud Scheduler 任务状态："
JOB_EXISTS=$(gcloud scheduler jobs describe weekly-preview-job \
  --location=us-central1 \
  --format="value(name)" 2>/dev/null || echo "")

if [ -n "$JOB_EXISTS" ]; then
  echo "✅ 定时任务已创建"
  gcloud scheduler jobs describe weekly-preview-job \
    --location=us-central1 \
    --format="table(name,schedule,timeZone,state)"
else
  echo "❌ 定时任务尚未创建"
fi

echo ""

# 检查最近的构建
echo "🔨 最近的 Cloud Build："
gcloud builds list --limit=1 \
  --format="table(id,status,createTime,duration)" \
  --filter="source.repoSource.repoName:*weekly* OR substitutions._SERVICE_NAME:*weekly* OR images:*weekly*" 2>/dev/null || \
gcloud builds list --limit=1 \
  --format="table(id,status,createTime,duration)"

echo ""
echo "📋 Token 信息："
if [ -f secrets.env ]; then
  grep "^SCHEDULER_TOKEN=" secrets.env
else
  echo "⚠️  secrets.env 文件不存在"
fi
