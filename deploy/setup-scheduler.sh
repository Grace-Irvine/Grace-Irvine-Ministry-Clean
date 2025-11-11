#!/bin/bash
# 配置 Cloud Scheduler 自动运行数据清洗任务
# 每30分钟自动运行

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Cloud Scheduler 配置脚本${NC}"
echo -e "${BLUE}============================================${NC}"

# 配置参数
PROJECT_ID="${GCP_PROJECT_ID:-ai-for-god}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="ministry-data-cleaning"
JOB_NAME="ministry-data-cleaning-scheduler"

# 服务URL（从 Cloud Run 服务自动获取）
if [ -z "$SERVICE_URL" ]; then
    echo -e "${YELLOW}从 Cloud Run 服务获取 URL...${NC}"
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.url)" 2>/dev/null || echo "")
    
    if [ -z "$SERVICE_URL" ]; then
        echo -e "${RED}错误: 无法获取服务 URL，请手动设置 SERVICE_URL 环境变量${NC}"
        exit 1
    fi
fi

# Scheduler Token (从 Secret Manager 读取)
SECRET_NAME="api-scheduler-token"
echo -e "${YELLOW}从 Secret Manager 读取 token...${NC}"
if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    SCHEDULER_TOKEN=$(gcloud secrets versions access latest --secret="$SECRET_NAME" --project="$PROJECT_ID" 2>/dev/null || echo "")
    if [ -z "$SCHEDULER_TOKEN" ]; then
        echo -e "${RED}错误: 无法从 Secret Manager 读取 token${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ 成功从 Secret Manager 读取 token${NC}"
else
    echo -e "${RED}错误: Secret '$SECRET_NAME' 不存在${NC}"
    echo -e "${YELLOW}请先运行 ./deploy/setup-secrets.sh 创建 secret${NC}"
    exit 1
fi

# 调度配置
SCHEDULE="*/30 * * * *"  # 每30分钟
TIMEZONE="America/Los_Angeles"
DESCRIPTION="Ministry data cleaning job - runs every 30 minutes"

echo -e "\n${GREEN}配置信息:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Job Name: $JOB_NAME"
echo "  Service URL: $SERVICE_URL"
echo "  Schedule: $SCHEDULE ($TIMEZONE)"
echo "  Token: ${SCHEDULER_TOKEN:0:20}... (从 Secret Manager 读取)"
echo ""

# 检查是否已存在scheduler job
echo -e "${YELLOW}检查现有作业...${NC}"
if gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" &>/dev/null; then
    echo -e "${YELLOW}作业已存在，将更新配置${NC}"

    # 更新现有作业
    gcloud scheduler jobs update http "$JOB_NAME" \
        --location="$REGION" \
        --schedule="$SCHEDULE" \
        --time-zone="$TIMEZONE" \
        --uri="${SERVICE_URL}/trigger-cleaning" \
        --http-method=POST \
        --update-headers="Authorization=Bearer ${SCHEDULER_TOKEN},Content-Type=application/json" \
        --description="$DESCRIPTION"

    echo -e "${GREEN}✓ 作业更新成功${NC}"
else
    echo -e "${YELLOW}创建新作业...${NC}"

    # 创建新作业
    gcloud scheduler jobs create http "$JOB_NAME" \
        --location="$REGION" \
        --schedule="$SCHEDULE" \
        --time-zone="$TIMEZONE" \
        --uri="${SERVICE_URL}/trigger-cleaning" \
        --http-method=POST \
        --headers="Authorization=Bearer ${SCHEDULER_TOKEN},Content-Type=application/json" \
        --description="$DESCRIPTION"

    echo -e "${GREEN}✓ 作业创建成功${NC}"
fi

echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}Cloud Scheduler 配置完成${NC}"
echo -e "${GREEN}============================================${NC}"

echo -e "\n${YELLOW}作业信息:${NC}"
gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" --format="table(
    name,
    schedule,
    timeZone,
    httpTarget.uri,
    state,
    lastAttemptTime,
    status
)"

echo -e "\n${YELLOW}下一步:${NC}"
echo "  1. 手动测试作业:"
echo "     gcloud scheduler jobs run $JOB_NAME --location=$REGION"
echo ""
echo "  2. 查看作业日志:"
echo "     gcloud logging read \"resource.type=cloud_scheduler_job AND resource.labels.job_id=$JOB_NAME\" --limit 50"
echo ""
echo "  3. 暂停作业:"
echo "     gcloud scheduler jobs pause $JOB_NAME --location=$REGION"
echo ""
echo "  4. 恢复作业:"
echo "     gcloud scheduler jobs resume $JOB_NAME --location=$REGION"
echo ""

echo -e "${BLUE}============================================${NC}"
