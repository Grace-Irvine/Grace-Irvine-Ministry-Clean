#!/bin/bash
# 配置 Cloud Scheduler 自动运行数据清洗任务
# 每周日凌晨2点自动运行

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

# 服务URL
SERVICE_URL="https://ministry-data-cleaning-760303847302.us-central1.run.app"

# Scheduler Token (从Cloud Run环境变量中获取)
SCHEDULER_TOKEN="cfa09ce3aa0648d9fe784b3af1975c7534621c5c64b9c0c15446ad8b3908c2f3"

# 调度配置
SCHEDULE="0 2 * * 0"  # 每周日凌晨2点
TIMEZONE="America/Los_Angeles"
DESCRIPTION="Weekly ministry data cleaning job - runs every Sunday at 2 AM"

echo -e "\n${GREEN}配置信息:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Job Name: $JOB_NAME"
echo "  Service URL: $SERVICE_URL"
echo "  Schedule: $SCHEDULE ($TIMEZONE)"
echo "  Token: ${SCHEDULER_TOKEN:0:20}..."
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
        --uri="${SERVICE_URL}/api/v1/clean" \
        --http-method=POST \
        --headers="Content-Type=application/json,X-Scheduler-Token=${SCHEDULER_TOKEN}" \
        --message-body='{"dry_run": false}' \
        --description="$DESCRIPTION"

    echo -e "${GREEN}✓ 作业更新成功${NC}"
else
    echo -e "${YELLOW}创建新作业...${NC}"

    # 创建新作业
    gcloud scheduler jobs create http "$JOB_NAME" \
        --location="$REGION" \
        --schedule="$SCHEDULE" \
        --time-zone="$TIMEZONE" \
        --uri="${SERVICE_URL}/api/v1/clean" \
        --http-method=POST \
        --headers="Content-Type=application/json,X-Scheduler-Token=${SCHEDULER_TOKEN}" \
        --message-body='{"dry_run": false}' \
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
