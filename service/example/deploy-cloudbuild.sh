#!/bin/bash
# 使用 Cloud Build 构建并部署每周事工预览定时器服务
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

# 设置默认值
REGION=${REGION:-us-central1}
SERVICE_NAME=${SERVICE_NAME:-weekly-preview-scheduler}

echo -e "${GREEN}项目 ID: $PROJECT_ID${NC}"
echo -e "${GREEN}配置信息:${NC}"
echo "  MCP Server: $MCP_SERVER_URL"
echo "  发件人: $EMAIL_FROM"
echo "  收件人: $EMAIL_TO"
if [ -n "$EMAIL_CC" ]; then
  echo "  抄送: $EMAIL_CC"
fi
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

echo -e "${GREEN}提交到 Cloud Build 构建镜像...${NC}"
cd "$PROJECT_ROOT"

IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"

# 使用 gcloud builds submit 构建并推送镜像
# 这不需要本地 Docker daemon
gcloud builds submit \
  --config "mcp/example/cloudbuild.yaml" \
  .

echo -e "${GREEN}部署到 Cloud Run...${NC}"

# 构建环境变量字符串
ENV_VARS="MCP_SERVER_URL=$MCP_SERVER_URL,MCP_BEARER_TOKEN=$MCP_BEARER_TOKEN,SMTP_SERVER=${SMTP_SERVER:-smtp.gmail.com},SMTP_PORT=${SMTP_PORT:-587},SMTP_USER=$SMTP_USER,SMTP_PASSWORD=$SMTP_PASSWORD,EMAIL_FROM=$EMAIL_FROM,EMAIL_TO=$EMAIL_TO,SCHEDULER_TOKEN=$SCHEDULER_TOKEN"

if [ -n "$EMAIL_CC" ]; then
  ENV_VARS="$ENV_VARS,EMAIL_CC=$EMAIL_CC"
fi

gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_TAG" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 1 \
  --set-env-vars "$ENV_VARS"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"

# 获取服务 URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" \
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
    --location="$REGION" \
    --format="value(name)" 2>/dev/null || echo "")
  
  if [ -z "$JOB_EXISTS" ]; then
    echo -e "${GREEN}创建 Cloud Scheduler 任务...${NC}"
    gcloud scheduler jobs create http "$JOB_NAME" \
      --location="$REGION" \
      --schedule="0 9 * * 1" \
      --uri="$SERVICE_URL/trigger" \
      --http-method=POST \
      --headers="Authorization=Bearer $SCHEDULER_TOKEN" \
      --time-zone="America/Los_Angeles" \
      --description="每周一早上9点触发事工预览生成和邮件发送"
  else
    echo -e "${GREEN}更新 Cloud Scheduler 任务...${NC}"
    gcloud scheduler jobs update http "$JOB_NAME" \
      --location="$REGION" \
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
  echo "测试触发:"
  echo "  curl -X POST \"$SERVICE_URL/trigger\" \\"
  echo "    -H \"Authorization: Bearer $SCHEDULER_TOKEN\" \\"
  echo "    -H \"Content-Type: application/json\""
fi
