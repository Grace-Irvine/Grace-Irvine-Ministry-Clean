#!/bin/bash
# Google Cloud Scheduler 设置脚本
# 创建定时任务，每30分钟检查并更新数据

set -e

# ============================================================
# 配置变量
# ============================================================

# 项目配置
PROJECT_ID="${GCP_PROJECT_ID:-ai-for-god}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="ministry-data-cleaning"

# 定时任务配置
JOB_NAME="ministry-data-cleaning-scheduler"
SCHEDULE="*/30 * * * *"  # 每30分钟执行一次
TIME_ZONE="Asia/Shanghai"  # 北京时间

# 获取 Service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --format="value(status.url)" 2>/dev/null || echo "")

if [ -z "$SERVICE_URL" ]; then
    echo "错误：无法获取 Cloud Run 服务 URL"
    echo "请确保服务已部署: $SERVICE_NAME"
    exit 1
fi

# 认证令牌
SCHEDULER_TOKEN="${SCHEDULER_TOKEN:-}"

if [ -z "$SCHEDULER_TOKEN" ]; then
    echo "警告：未设置 SCHEDULER_TOKEN 环境变量"
    echo "定时任务将无法通过认证"
    echo "请先运行: export SCHEDULER_TOKEN='your-token'"
    echo ""
    read -p "是否继续创建不带认证的定时任务？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ============================================================
# 函数定义
# ============================================================

print_header() {
    echo ""
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

# ============================================================
# 主流程
# ============================================================

print_header "设置 Google Cloud Scheduler"

echo "项目 ID: $PROJECT_ID"
echo "区域: $REGION"
echo "服务 URL: $SERVICE_URL"
echo "定时任务名称: $JOB_NAME"
echo "执行频率: 每30分钟"
echo "时区: $TIME_ZONE"
echo ""

# 1. 设置项目
print_header "1. 设置 GCP 项目"
gcloud config set project "$PROJECT_ID"

# 2. 启用 Cloud Scheduler API
print_header "2. 启用 Cloud Scheduler API"
gcloud services enable cloudscheduler.googleapis.com

# 3. 创建或更新定时任务
print_header "3. 创建定时任务"

# 检查任务是否已存在
if gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" &> /dev/null; then
    echo "定时任务已存在，将更新配置..."
    
    if [ -n "$SCHEDULER_TOKEN" ]; then
        # 带认证令牌
        gcloud scheduler jobs update http "$JOB_NAME" \
            --location="$REGION" \
            --schedule="$SCHEDULE" \
            --time-zone="$TIME_ZONE" \
            --uri="${SERVICE_URL}/trigger-cleaning" \
            --http-method=POST \
            --headers="Authorization=Bearer ${SCHEDULER_TOKEN},Content-Type=application/json" \
            --max-retry-attempts=3 \
            --min-backoff=30s
    else
        # 不带认证令牌
        gcloud scheduler jobs update http "$JOB_NAME" \
            --location="$REGION" \
            --schedule="$SCHEDULE" \
            --time-zone="$TIME_ZONE" \
            --uri="${SERVICE_URL}/trigger-cleaning" \
            --http-method=POST \
            --headers="Content-Type=application/json" \
            --max-retry-attempts=3 \
            --min-backoff=30s
    fi
    
    echo "✓ 定时任务已更新"
else
    echo "创建新的定时任务..."
    
    if [ -n "$SCHEDULER_TOKEN" ]; then
        # 带认证令牌
        gcloud scheduler jobs create http "$JOB_NAME" \
            --location="$REGION" \
            --schedule="$SCHEDULE" \
            --time-zone="$TIME_ZONE" \
            --uri="${SERVICE_URL}/trigger-cleaning" \
            --http-method=POST \
            --headers="Authorization=Bearer ${SCHEDULER_TOKEN},Content-Type=application/json" \
            --max-retry-attempts=3 \
            --min-backoff=30s \
            --description="每30分钟检查并更新教会主日事工数据"
    else
        # 不带认证令牌
        gcloud scheduler jobs create http "$JOB_NAME" \
            --location="$REGION" \
            --schedule="$SCHEDULE" \
            --time-zone="$TIME_ZONE" \
            --uri="${SERVICE_URL}/trigger-cleaning" \
            --http-method=POST \
            --headers="Content-Type=application/json" \
            --max-retry-attempts=3 \
            --min-backoff=30s \
            --description="每30分钟检查并更新教会主日事工数据"
    fi
    
    echo "✓ 定时任务已创建"
fi

# 4. 显示任务详情
print_header "4. 定时任务详情"
gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION"

# 5. 完成
print_header "设置完成"

echo ""
echo "✅ Cloud Scheduler 已配置成功！"
echo ""
echo "定时任务详情："
echo "  名称: $JOB_NAME"
echo "  执行频率: 每30分钟"
echo "  下次执行: $(gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" --format="value(scheduleTime)")"
echo "  状态: $(gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" --format="value(state)")"
echo ""
echo "管理命令："
echo "  # 手动触发任务"
echo "  gcloud scheduler jobs run $JOB_NAME --location=$REGION"
echo ""
echo "  # 暂停任务"
echo "  gcloud scheduler jobs pause $JOB_NAME --location=$REGION"
echo ""
echo "  # 恢复任务"
echo "  gcloud scheduler jobs resume $JOB_NAME --location=$REGION"
echo ""
echo "  # 查看任务日志"
echo "  gcloud logging read \"resource.type=cloud_scheduler_job AND resource.labels.job_id=$JOB_NAME\" --limit 10"
echo ""
echo "  # 删除任务"
echo "  gcloud scheduler jobs delete $JOB_NAME --location=$REGION"
echo ""
echo "监控："
echo "  Cloud Scheduler 控制台: https://console.cloud.google.com/cloudscheduler?project=$PROJECT_ID"
echo "  Cloud Run 日志: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/logs?project=$PROJECT_ID"
echo ""
