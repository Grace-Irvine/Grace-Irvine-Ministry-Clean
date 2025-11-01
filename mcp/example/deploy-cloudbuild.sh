#!/bin/bash
# 使用 Cloud Build 部署每周事工预览定时器服务（无需本地 Docker）
# 使用方法: ./deploy-cloudbuild.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}使用 Cloud Build 部署服务${NC}"
echo -e "${GREEN}========================================${NC}"

# 加载配置文件
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SECRETS_FILE="$SCRIPT_DIR/secrets.env"

if [ ! -f "$SECRETS_FILE" ]; then
  echo -e "${RED}错误: 未找到 secrets.env 配置文件${NC}"
  exit 1
fi

echo -e "${GREEN}加载配置文件...${NC}"
source "$SCRIPT_DIR/load-secrets.sh"

# 获取项目 ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
  echo -e "${RED}错误: 未设置 GCP 项目 ID${NC}"
  exit 1
fi

echo -e "${GREEN}项目 ID: $PROJECT_ID${NC}"
echo -e "${GREEN}配置信息:${NC}"
echo "  MCP Server: $MCP_SERVER_URL"
echo "  发件人: $EMAIL_FROM"
echo "  收件人: $EMAIL_TO"
echo "  Scheduler Token: ${SCHEDULER_TOKEN:0:20}..."
echo ""

# 获取项目根目录
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# 确认部署
read -p "是否继续部署? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "已取消部署"
  exit 1
fi

echo -e "${GREEN}提交到 Cloud Build...${NC}"
cd "$PROJECT_ROOT"

# 使用 Cloud Build 构建和部署
gcloud builds submit \
  --config=mcp/example/cloudbuild.yaml \
  --substitutions=_MCP_SERVER_URL="$MCP_SERVER_URL",_MCP_BEARER_TOKEN="$MCP_BEARER_TOKEN",_SMTP_SERVER="$SMTP_SERVER",_SMTP_PORT="$SMTP_PORT",_SMTP_USER="$SMTP_USER",_SMTP_PASSWORD="$SMTP_PASSWORD",_EMAIL_FROM="$EMAIL_FROM",_EMAIL_TO="$EMAIL_TO",_SCHEDULER_TOKEN="$SCHEDULER_TOKEN"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"

# 获取服务 URL
SERVICE_URL=$(gcloud run services describe weekly-preview-scheduler \
  --region us-central1 \
  --format 'value(status.url)' 2>/dev/null || echo "")

if [ -n "$SERVICE_URL" ]; then
  echo ""
  echo "服务 URL: $SERVICE_URL"
  echo "健康检查: $SERVICE_URL/health"
  echo ""
  echo "现在创建 Cloud Scheduler 任务..."
  
  # 创建或更新 Cloud Scheduler 任务
  JOB_NAME="weekly-preview-job"
  JOB_EXISTS=$(gcloud scheduler jobs describe "$JOB_NAME" \
    --location=us-central1 \
    --format="value(name)" 2>/dev/null || echo "")
  
  if [ -z "$JOB_EXISTS" ]; then
    echo -e "${GREEN}创建 Cloud Scheduler 任务...${NC}"
    gcloud scheduler jobs create http "$JOB_NAME" \
      --location=us-central1 \
      --schedule="0 9 * * 1" \
      --uri="$SERVICE_URL/trigger" \
      --http-method=POST \
      --headers="Authorization=Bearer $SCHEDULER_TOKEN" \
      --time-zone="America/Los_Angeles" \
      --description="每周一早上9点触发事工预览生成和邮件发送"
  else
    echo -e "${GREEN}更新 Cloud Scheduler 任务...${NC}"
    gcloud scheduler jobs update http "$JOB_NAME" \
      --location=us-central1 \
      --schedule="0 9 * * 1" \
      --uri="$SERVICE_URL/trigger" \
      --http-method=POST \
      --headers="Authorization=Bearer $SCHEDULER_TOKEN" \
      --time-zone="America/Los_Angeles"
  fi
  
  echo ""
  echo "✅ 部署完成！"
  echo ""
  echo "服务 URL: $SERVICE_URL"
  echo "健康检查: $SERVICE_URL/health"
  echo "触发器端点: $SERVICE_URL/trigger"
  echo ""
  echo "SCHEDULER_TOKEN: $SCHEDULER_TOKEN"
  echo ""
  echo "测试触发:"
  echo "  curl -X POST \"$SERVICE_URL/trigger\" \\"
  echo "    -H \"Authorization: Bearer $SCHEDULER_TOKEN\" \\"
  echo "    -H \"Content-Type: application/json\""
fi
