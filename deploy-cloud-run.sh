#!/bin/bash
# Google Cloud Run 部署脚本

set -e  # 遇到错误立即退出

# ============================================================
# 配置变量（请根据实际情况修改）
# ============================================================

# 项目配置
PROJECT_ID="${GCP_PROJECT_ID:-ai-for-god}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="ministry-data-cleaning"

# 容器镜像配置
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Cloud Run 配置
MEMORY="1Gi"
CPU="1"
MAX_INSTANCES="3"
TIMEOUT="600s"  # 10 分钟超时（数据处理可能需要较长时间）

# 环境变量（安全令牌，用于 Cloud Scheduler 认证）
SCHEDULER_TOKEN="${SCHEDULER_TOKEN:-$(openssl rand -hex 32)}"

# 服务账号配置
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-ministry-cleaning-sa@${PROJECT_ID}.iam.gserviceaccount.com}"

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
        echo "安装指南：https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "错误：未找到 docker 命令，请先安装 Docker"
        exit 1
    fi
}

# ============================================================
# 主流程
# ============================================================

print_header "开始部署到 Google Cloud Run"

# 检查依赖
check_gcloud
check_docker

# 显示配置
echo "项目 ID: $PROJECT_ID"
echo "区域: $REGION"
echo "服务名称: $SERVICE_NAME"
echo "镜像: $IMAGE_NAME"
echo ""

# 1. 设置项目
print_header "1. 设置 GCP 项目"
gcloud config set project "$PROJECT_ID"

# 2. 启用必要的 API
print_header "2. 启用必要的 Google Cloud API"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com

# 3. 创建服务账号（如果不存在）
print_header "3. 创建或验证服务账号"
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT" &> /dev/null; then
    echo "创建服务账号: $SERVICE_ACCOUNT"
    gcloud iam service-accounts create ministry-cleaning-sa \
        --display-name="Ministry Data Cleaning Service Account"
    
    # 授予 Google Sheets 访问权限
    # 注意：您还需要在 Google Sheets 中手动添加此服务账号为协作者
    echo "服务账号创建成功"
else
    echo "服务账号已存在"
fi

# 4. 验证服务账号密钥文件
print_header "4. 验证服务账号密钥文件"
if [ -f "config/service-account.json" ]; then
    echo "✓ 服务账号密钥文件存在: config/service-account.json"
    echo "  该文件将被复制到 Docker 镜像中"
else
    echo "⚠️  警告：未找到 config/service-account.json"
    echo "  请确保该文件存在，否则应用无法访问 Google Sheets"
    exit 1
fi

# 5. 构建容器镜像
print_header "5. 构建 Docker 镜像"
gcloud builds submit --tag "$IMAGE_NAME" .

# 6. 部署到 Cloud Run
print_header "6. 部署到 Cloud Run"
gcloud run deploy "$SERVICE_NAME" \
    --image="$IMAGE_NAME" \
    --platform=managed \
    --region="$REGION" \
    --memory="$MEMORY" \
    --cpu="$CPU" \
    --max-instances="$MAX_INSTANCES" \
    --timeout="$TIMEOUT" \
    --service-account="$SERVICE_ACCOUNT" \
    --set-env-vars="SCHEDULER_TOKEN=${SCHEDULER_TOKEN},CONFIG_PATH=/app/config/config.json" \
    --allow-unauthenticated

# 7. 获取服务 URL
print_header "7. 获取服务信息"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --format="value(status.url)")

echo ""
echo "✅ 部署成功！"
echo ""
echo "服务 URL: $SERVICE_URL"
echo "API 文档: ${SERVICE_URL}/docs"
echo "健康检查: ${SERVICE_URL}/health"
echo ""
echo "⚠️  下一步："
echo "1. 保存 SCHEDULER_TOKEN 以供 Cloud Scheduler 使用："
echo "   export SCHEDULER_TOKEN='${SCHEDULER_TOKEN}'"
echo ""
echo "2. 测试 API 端点："
echo "   # 健康检查"
echo "   curl ${SERVICE_URL}/health"
echo ""
echo "   # 测试数据清洗 (dry-run)"
echo "   curl -X POST \"${SERVICE_URL}/api/v1/clean\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"dry_run\": true}'"
echo ""
echo "3. 设置 Cloud Scheduler (可选)："
echo "   ./setup-cloud-scheduler.sh"
echo ""
echo "4. 查看部署详情："
echo "   cat DEPLOYMENT_SUCCESS.md"
echo ""

