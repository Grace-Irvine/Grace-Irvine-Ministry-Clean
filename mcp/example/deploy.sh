#!/bin/bash
# 部署每周事工预览定时器服务到 Cloud Run
# 使用方法: ./deploy.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}每周事工预览定时器服务部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 尝试加载 secrets.env 配置文件（如果存在）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SECRETS_FILE="$SCRIPT_DIR/secrets.env"

if [ -f "$SECRETS_FILE" ]; then
  echo -e "${GREEN}从配置文件加载配置信息...${NC}"
  source "$SCRIPT_DIR/load-secrets.sh"
else
  echo -e "${RED}错误: 未找到 secrets.env 配置文件${NC}"
  echo ""
  echo "请先创建配置文件："
  echo "  1. cp secrets.env.example secrets.env"
  echo "  2. 编辑 secrets.env 并填入必需信息"
  echo "  3. chmod 600 secrets.env"
  echo ""
  echo "或者设置环境变量："
  echo "  export SMTP_PASSWORD=..."
  echo "  export EMAIL_TO=..."
  echo "  export SCHEDULER_TOKEN=..."
  exit 1
fi

# 检查必需的环境变量（没有默认值的）
REQUIRED_VARS=(
  "SMTP_PASSWORD"
  "EMAIL_TO"
  "SCHEDULER_TOKEN"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    MISSING_VARS+=("$var")
  fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
  echo -e "${RED}错误: 以下环境变量未设置:${NC}"
  printf '%s\n' "${MISSING_VARS[@]}"
  echo ""
  echo ""
  echo "请在 secrets.env 文件中设置这些变量："
  echo "  SMTP_PASSWORD=your-app-password"
  echo "  EMAIL_TO=recipient@example.com"
  echo "  SCHEDULER_TOKEN=your-secure-token"
  echo ""
  echo "配置文件应该包含所有必需配置，请参考 secrets.env.example"
  exit 1
fi

# 显示使用的配置
echo -e "${GREEN}配置信息:${NC}"
echo "  MCP_SERVER_URL: $MCP_SERVER_URL"
echo "  MCP_BEARER_TOKEN: ${MCP_BEARER_TOKEN:0:20}..."
echo "  EMAIL_FROM: $EMAIL_FROM"
echo "  SMTP_USER: $SMTP_USER"
echo "  EMAIL_TO: $EMAIL_TO"
echo "  EMAIL_CC: ${EMAIL_CC:-未设置}"
echo ""

# 获取项目 ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
  echo -e "${RED}错误: 未设置 GCP 项目 ID${NC}"
  echo "请运行: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo -e "${GREEN}项目 ID: $PROJECT_ID${NC}"

# 设置其他默认值
REGION=${REGION:-us-central1}
SERVICE_NAME=${SERVICE_NAME:-weekly-preview-scheduler}
SCHEDULE=${SCHEDULE:-"0 9 * * 1"}  # 每周一早上9点
TIME_ZONE=${TIME_ZONE:-America/Los_Angeles}

echo -e "${YELLOW}配置:${NC}"
echo "  服务名称: $SERVICE_NAME"
echo "  区域: $REGION"
echo "  调度: $SCHEDULE ($TIME_ZONE)"

# 确认
read -p "是否继续部署? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "已取消部署"
  exit 1
fi

# 获取根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo -e "${GREEN}构建 Docker 镜像...${NC}"
cd "$PROJECT_ROOT"

# 构建镜像
IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"
docker build -t "$IMAGE_TAG" -f "$SCRIPT_DIR/Dockerfile" .

echo -e "${GREEN}推送镜像到 GCR...${NC}"
docker push "$IMAGE_TAG"

echo -e "${GREEN}部署到 Cloud Run...${NC}"
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
  --set-env-vars "MCP_SERVER_URL=$MCP_SERVER_URL,MCP_BEARER_TOKEN=$MCP_BEARER_TOKEN,SMTP_SERVER=${SMTP_SERVER:-smtp.gmail.com},SMTP_PORT=${SMTP_PORT:-587},SMTP_USER=$SMTP_USER,SMTP_PASSWORD=$SMTP_PASSWORD,EMAIL_FROM=$EMAIL_FROM,EMAIL_TO=$EMAIL_TO,SCHEDULER_TOKEN=$SCHEDULER_TOKEN"

# 获取服务 URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" \
  --format 'value(status.url)')

echo -e "${GREEN}服务已部署: $SERVICE_URL${NC}"

# 创建或更新 Cloud Scheduler 任务
JOB_NAME="weekly-preview-job"
JOB_EXISTS=$(gcloud scheduler jobs describe "$JOB_NAME" \
  --location="$REGION" \
  --format="value(name)" 2>/dev/null || echo "")

if [ -z "$JOB_EXISTS" ]; then
  echo -e "${GREEN}创建 Cloud Scheduler 任务...${NC}"
  gcloud scheduler jobs create http "$JOB_NAME" \
    --location="$REGION" \
    --schedule="$SCHEDULE" \
    --uri="$SERVICE_URL/trigger" \
    --http-method=POST \
    --headers="Authorization=Bearer $SCHEDULER_TOKEN" \
    --time-zone="$TIME_ZONE" \
    --description="每周一早上9点触发事工预览生成和邮件发送"
else
  echo -e "${GREEN}更新 Cloud Scheduler 任务...${NC}"
  gcloud scheduler jobs update http "$JOB_NAME" \
    --location="$REGION" \
    --schedule="$SCHEDULE" \
    --uri="$SERVICE_URL/trigger" \
    --http-method=POST \
    --headers="Authorization=Bearer $SCHEDULER_TOKEN" \
    --time-zone="$TIME_ZONE"
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "服务 URL: $SERVICE_URL"
echo "健康检查: $SERVICE_URL/health"
echo "触发器端点: $SERVICE_URL/trigger"
echo ""
echo "测试触发:"
echo "  curl -X POST \"$SERVICE_URL/trigger\" \\"
echo "    -H \"Authorization: Bearer $SCHEDULER_TOKEN\" \\"
echo "    -H \"Content-Type: application/json\""
echo ""
echo "查看日志:"
echo "  gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit 50"
