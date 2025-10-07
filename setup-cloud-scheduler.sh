#!/bin/bash
# Google Cloud Scheduler 设置脚本
# 创建定时任务，每小时触发数据清洗

set -e  # 遇到错误立即退出

# ============================================================
# 配置变量（请根据实际情况修改）
# ============================================================

# 项目配置
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="ministry-data-cleaning"

# Cloud Scheduler 配置
JOB_NAME="ministry-cleaning-hourly"
SCHEDULE="0 * * * *"  # 每小时运行一次（可修改为需要的频率）
TIMEZONE="America/Los_Angeles"  # 时区（请根据实际情况修改）

# 认证令牌
SCHEDULER_TOKEN="${SCHEDULER_TOKEN}"

# 服务 URL
SERVICE_URL="${SERVICE_URL}"

# ============================================================
# 函数定义
# ============================================================

print_header() {
    echo ""
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        echo "错误：未找到 gcloud 命令，请先安装 Google Cloud SDK"
        exit 1
    fi
}

# ============================================================
# 主流程
# ============================================================

print_header "设置 Google Cloud Scheduler"

# 检查依赖
check_gcloud

# 如果未提供 SERVICE_URL，自动获取
if [ -z "$SERVICE_URL" ]; then
    echo "获取 Cloud Run 服务 URL..."
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)" 2>/dev/null || echo "")
    
    if [ -z "$SERVICE_URL" ]; then
        echo "错误：无法获取服务 URL，请确保服务已部署或手动设置 SERVICE_URL"
        exit 1
    fi
fi

# 检查 SCHEDULER_TOKEN
if [ -z "$SCHEDULER_TOKEN" ]; then
    echo "错误：未设置 SCHEDULER_TOKEN 环境变量"
    echo "请运行: export SCHEDULER_TOKEN='your-token-here'"
    exit 1
fi

# 显示配置
echo "项目 ID: $PROJECT_ID"
echo "区域: $REGION"
echo "服务名称: $SERVICE_NAME"
echo "服务 URL: $SERVICE_URL"
echo "定时任务名称: $JOB_NAME"
echo "执行频率: $SCHEDULE"
echo "时区: $TIMEZONE"
echo ""

# 确认继续
read -p "确认以上配置是否正确？(y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消设置"
    exit 1
fi

# 1. 设置项目
print_header "1. 设置 GCP 项目"
gcloud config set project "$PROJECT_ID"

# 2. 启用 Cloud Scheduler API
print_header "2. 启用 Cloud Scheduler API"
gcloud services enable cloudscheduler.googleapis.com

# 3. 删除现有任务（如果存在）
print_header "3. 检查并删除现有任务"
if gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" &> /dev/null; then
    echo "删除现有任务: $JOB_NAME"
    gcloud scheduler jobs delete "$JOB_NAME" --location="$REGION" --quiet
fi

# 4. 创建新的定时任务
print_header "4. 创建定时任务"
gcloud scheduler jobs create http "$JOB_NAME" \
    --location="$REGION" \
    --schedule="$SCHEDULE" \
    --time-zone="$TIMEZONE" \
    --uri="${SERVICE_URL}/trigger-cleaning" \
    --http-method=POST \
    --headers="Content-Type=application/json,Authorization=Bearer ${SCHEDULER_TOKEN}" \
    --description="每小时触发教会主日事工数据清洗任务"

# 5. 测试任务
print_header "5. 测试定时任务"
echo "手动触发一次任务进行测试..."
gcloud scheduler jobs run "$JOB_NAME" --location="$REGION"

echo ""
echo "✅ Cloud Scheduler 设置成功！"
echo ""
echo "任务详情："
echo "  名称: $JOB_NAME"
echo "  执行频率: $SCHEDULE ($TIMEZONE)"
echo "  目标 URL: ${SERVICE_URL}/trigger-cleaning"
echo ""
echo "查看任务状态："
echo "  gcloud scheduler jobs describe $JOB_NAME --location=$REGION"
echo ""
echo "查看执行日志："
echo "  gcloud logging read \"resource.type=cloud_scheduler_job AND resource.labels.job_id=$JOB_NAME\" --limit 10"
echo ""
echo "暂停任务："
echo "  gcloud scheduler jobs pause $JOB_NAME --location=$REGION"
echo ""
echo "恢复任务："
echo "  gcloud scheduler jobs resume $JOB_NAME --location=$REGION"
echo ""

# 6. 显示 Cron 表达式说明
print_header "Cron 表达式参考"
echo "当前设置: $SCHEDULE"
echo ""
echo "常用频率："
echo "  每小时:    0 * * * *"
echo "  每天 2 AM: 0 2 * * *"
echo "  每周一:    0 0 * * 1"
echo "  每 30 分钟: */30 * * * *"
echo ""
echo "修改频率："
echo "  gcloud scheduler jobs update http $JOB_NAME \\"
echo "    --location=$REGION \\"
echo "    --schedule='YOUR_CRON_EXPRESSION'"
echo ""

