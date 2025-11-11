#!/bin/bash
# API Service Cloud Run 部署脚本
# 部署数据清洗和管理API服务

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
DOCKERFILE_PATH="api/Dockerfile"

# Cloud Run 配置
MEMORY="1Gi"
CPU="1"
MAX_INSTANCES="3"
TIMEOUT="600s"  # 10 分钟超时（数据处理可能需要较长时间）

# 环境变量（不再设置 SCHEDULER_TOKEN，让服务从 Secret Manager 读取）
# SCHEDULER_TOKEN 将从 Secret Manager 的 api-scheduler-token 读取

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

# 3. 启用 Secret Manager API（如果尚未启用）
print_header "3. 启用 Secret Manager API"
gcloud services enable secretmanager.googleapis.com || true
echo "Secret Manager API 已启用"

# 4. 创建服务账号（如果不存在）
print_header "4. 创建或验证服务账号"
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

# 授予服务账号 Secret Manager 访问权限
CLOUD_RUN_SA="${PROJECT_ID}@appspot.gserviceaccount.com"
echo "授予 Secret Manager 访问权限..."
if gcloud secrets describe api-scheduler-token --project="$PROJECT_ID" &> /dev/null; then
    gcloud secrets add-iam-policy-binding api-scheduler-token \
        --member="serviceAccount:${CLOUD_RUN_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet || true
    echo "✓ Secret Manager 访问权限已配置"
else
    echo "⚠️  Secret 'api-scheduler-token' 不存在，请运行 ./deploy/setup-secrets.sh 创建"
fi

# 5. 验证服务账号密钥文件
print_header "5. 验证服务账号密钥文件"
if [ -f "config/service-account.json" ]; then
    echo "✓ 服务账号密钥文件存在: config/service-account.json"
    echo "  该文件将被复制到 Docker 镜像中"
else
    echo "⚠️  警告：未找到 config/service-account.json"
    echo "  请确保该文件存在，否则应用无法访问 Google Sheets"
    exit 1
fi

# 6. 构建容器镜像
print_header "6. 构建 Docker 镜像"
echo "使用 Dockerfile: $DOCKERFILE_PATH"
gcloud builds submit --config=api/cloudbuild.yaml --timeout=10m .

# 7. 部署到 Cloud Run
print_header "7. 部署到 Cloud Run"

# 设置环境变量（只设置 GCP_PROJECT_ID，让服务从 Secret Manager 读取 SCHEDULER_TOKEN）
ENV_VARS="GCP_PROJECT_ID=${PROJECT_ID}"

# 验证 Secret Manager 中的 token 是否存在
if ! gcloud secrets describe api-scheduler-token --project="$PROJECT_ID" &>/dev/null; then
    echo "⚠️  警告: Secret 'api-scheduler-token' 不存在"
    echo "  服务将无法从 Secret Manager 读取 token"
    echo "  请运行 ./deploy/setup-secrets.sh 创建 secret"
fi

gcloud run deploy "$SERVICE_NAME" \
    --image="$IMAGE_NAME" \
    --platform=managed \
    --region="$REGION" \
    --memory="$MEMORY" \
    --cpu="$CPU" \
    --max-instances="$MAX_INSTANCES" \
    --timeout="$TIMEOUT" \
    --service-account="$SERVICE_ACCOUNT" \
    --set-env-vars="$ENV_VARS" \
    --allow-unauthenticated

# 8. 获取服务 URL
print_header "8. 获取服务信息"
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
echo "1. 测试 API 端点："
echo "   # 健康检查"
echo "   curl ${SERVICE_URL}/health"
echo ""
echo "   # 测试数据清洗 (dry-run)"
echo "   curl -X POST \"${SERVICE_URL}/api/v1/clean\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"dry_run\": true}'"
echo ""
echo "2. 设置 Cloud Scheduler："
echo "   ./deploy/setup-scheduler.sh"
echo "   (脚本会自动从 Secret Manager 读取 token)"
echo ""
echo "3. 验证 Secret Manager 配置："
echo "   # 检查 secret 是否存在"
echo "   gcloud secrets describe api-scheduler-token --project=$PROJECT_ID"
echo ""
echo "   # 验证服务账号权限"
echo "   gcloud secrets get-iam-policy api-scheduler-token --project=$PROJECT_ID"
echo ""
echo "📝 注意："
echo "   - SCHEDULER_TOKEN 不再通过环境变量设置"
echo "   - 服务会自动从 Secret Manager 读取 api-scheduler-token"
echo "   - 确保 Cloud Run 服务账号有 Secret Manager 访问权限"
echo ""

