#!/bin/bash
# 部署 MCP Server 到 Google Cloud Run
# 使用 HTTP/SSE 传输层，支持远程 MCP 客户端访问

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MCP Server Cloud Run Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查必需的环境变量
if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID is not set${NC}"
    echo "Usage: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

if [ -z "$MCP_BEARER_TOKEN" ]; then
    echo -e "${YELLOW}Warning: MCP_BEARER_TOKEN is not set${NC}"
    echo "Service will automatically read from Secret Manager if available"
    # 检查 Secret Manager 中是否有 token
    if gcloud secrets describe mcp-bearer-token --project=$GCP_PROJECT_ID &> /dev/null 2>&1; then
        echo -e "${GREEN}✓ Secret 'mcp-bearer-token' exists in Secret Manager${NC}"
        echo "Service will use token from Secret Manager"
    else
        echo -e "${YELLOW}⚠️  Secret 'mcp-bearer-token' does not exist in Secret Manager${NC}"
        echo "Generate a secure token with: openssl rand -hex 32"
        if [ "${SKIP_CONFIRM:-false}" != "true" ]; then
            read -p "Enter Bearer Token (or press Enter to skip): " MCP_BEARER_TOKEN
            if [ -z "$MCP_BEARER_TOKEN" ]; then
                echo -e "${YELLOW}Deploying without authentication...${NC}"
            fi
        fi
    fi
fi

# 配置参数
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${MCP_SERVICE_NAME:-ministry-data-mcp}"
IMAGE_NAME="gcr.io/${GCP_PROJECT_ID}/${SERVICE_NAME}"
DOCKERFILE_PATH="service/Dockerfile"
MEMORY="${MEMORY:-512Mi}"
CPU="${CPU:-1}"
MAX_INSTANCES="${MAX_INSTANCES:-10}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
TIMEOUT="${TIMEOUT:-300}"

echo -e "\n${GREEN}Configuration:${NC}"
echo "  Project ID: $GCP_PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo "  Image: $IMAGE_NAME"
echo "  Memory: $MEMORY"
echo "  CPU: $CPU"
echo "  Auth Required: $([ -n "$MCP_BEARER_TOKEN" ] && echo 'Yes' || echo 'No')"

# 确认部署（非交互模式支持）
if [ "${SKIP_CONFIRM:-false}" != "true" ]; then
    read -p "Continue with deployment? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 1
    fi
fi

# 1. 检查 Google Cloud SDK
echo -e "\n${GREEN}[1/6] Checking Google Cloud SDK...${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# 设置项目
gcloud config set project $GCP_PROJECT_ID
echo -e "${GREEN}✓ Project set to $GCP_PROJECT_ID${NC}"

# 2. 启用必要的 API
echo -e "\n${GREEN}[2/6] Enabling required APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com || true
echo -e "${GREEN}✓ APIs enabled${NC}"

# 3. 构建 Docker 镜像
echo -e "\n${GREEN}[3/6] Building Docker image...${NC}"
echo "  Using Dockerfile: $DOCKERFILE_PATH"
gcloud builds submit \
    --config service/cloudbuild.yaml \
    --timeout=10m \
    .
echo -e "${GREEN}✓ Image built: $IMAGE_NAME${NC}"

# 4. 设置 Secret Manager (提前执行以确保部署时可用)
echo -e "\n${GREEN}[4/6] Setting up Secret Manager...${NC}"

CLOUD_RUN_SA="${GCP_PROJECT_ID}@appspot.gserviceaccount.com"
SECRET_CREATED=false

# 检查并授予 mcp-bearer-token 访问权限
if gcloud secrets describe mcp-bearer-token --project=$GCP_PROJECT_ID &> /dev/null 2>&1; then
    echo "  Secret 'mcp-bearer-token' exists"
    SECRET_CREATED=true
else
    echo -e "  ${YELLOW}⚠️  Secret 'mcp-bearer-token' does not exist${NC}"
    if [ -n "$MCP_BEARER_TOKEN" ]; then
        echo "  Creating new secret with provided token..."
        echo -n "$MCP_BEARER_TOKEN" | gcloud secrets create mcp-bearer-token \
            --data-file=- \
            --replication-policy="automatic" \
            --project=$GCP_PROJECT_ID
        SECRET_CREATED=true
        echo -e "  ${GREEN}✓ Bearer Token secret created${NC}"
    else
        echo -e "  ${YELLOW}  提示: 运行 ./deploy/setup-secrets.sh 创建 secrets${NC}"
        echo -e "  或设置 MCP_BEARER_TOKEN 环境变量后重新部署"
    fi
fi

if [ "$SECRET_CREATED" = true ]; then
    # 授予访问权限
    gcloud secrets add-iam-policy-binding mcp-bearer-token \
        --member="serviceAccount:${CLOUD_RUN_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet || true
    echo -e "  ${GREEN}✓ Secret Manager access configured${NC}"
fi

# 5. 部署到 Cloud Run
echo -e "\n${GREEN}[5/6] Deploying to Cloud Run...${NC}"

# 设置环境变量
ENV_VARS="GCP_PROJECT_ID=${GCP_PROJECT_ID},MCP_MODE=http,MCP_REQUIRE_AUTH=true"
# 注意：这里不再将 MCP_BEARER_TOKEN 放入 ENV_VARS，而是通过 secrets 注入

DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --memory $MEMORY \
    --cpu $CPU \
    --timeout $TIMEOUT \
    --max-instances $MAX_INSTANCES \
    --min-instances $MIN_INSTANCES \
    --set-env-vars ${ENV_VARS} \
    --allow-unauthenticated"

# 构建 secrets 列表
SECRETS_LIST=""

# 添加 Bearer Token（优先使用 Secrets）
if [ "$SECRET_CREATED" = true ] || [ -n "$MCP_BEARER_TOKEN" ]; then
    # 如果 secret 刚创建或已存在，且我们知道它
    if gcloud secrets describe mcp-bearer-token --project=$GCP_PROJECT_ID &> /dev/null 2>&1; then
        SECRETS_LIST="MCP_BEARER_TOKEN=mcp-bearer-token:latest"
    fi
fi

# 添加 service account secret（如果存在）
if gcloud secrets describe ministry-service-account --project=$GCP_PROJECT_ID &> /dev/null; then
    if [ -n "$SECRETS_LIST" ]; then
        SECRETS_LIST="$SECRETS_LIST,/app/config/service-account.json=ministry-service-account:latest"
    else
        SECRETS_LIST="/app/config/service-account.json=ministry-service-account:latest"
    fi
    echo "  Using existing ministry-service-account secret"
fi

# 添加所有 secrets（如果有）
if [ -n "$SECRETS_LIST" ]; then
    DEPLOY_CMD="$DEPLOY_CMD --update-secrets $SECRETS_LIST"
fi

# 执行部署
echo "Executing: $DEPLOY_CMD"
eval $DEPLOY_CMD
echo -e "${GREEN}✓ Service deployed${NC}"

# 6. 获取服务 URL
echo -e "\n${GREEN}[6/6] Getting service URL...${NC}"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --format 'value(status.url)')

echo -e "${GREEN}✓ Deployment complete!${NC}"

# 显示部署信息
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Service URL: ${YELLOW}${SERVICE_URL}${NC}"
echo -e "MCP Endpoints:"
echo -e "  - SSE (for OpenAI): ${YELLOW}${SERVICE_URL}/sse${NC}"
echo -e "  - Health Check: ${YELLOW}${SERVICE_URL}/health${NC}"
echo ""

# 测试健康检查
echo -e "${GREEN}Testing health endpoint...${NC}"
if [ -n "$MCP_BEARER_TOKEN" ]; then
    HEALTH_RESPONSE=$(curl -s -H "Authorization: Bearer $MCP_BEARER_TOKEN" "${SERVICE_URL}/health")
else
    # 如果没有本地 token，尝试不做 auth 请求（可能会失败如果 auth required）
    HEALTH_RESPONSE=$(curl -s "${SERVICE_URL}/health")
fi
echo -e "Health: ${YELLOW}${HEALTH_RESPONSE}${NC}"

# 生成客户端配置
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Client Configuration${NC}"
echo -e "${GREEN}========================================${NC}"

if [ -n "$MCP_BEARER_TOKEN" ]; then
    echo -e "\n${YELLOW}1. For OpenAI ChatGPT:${NC}"
    echo "   Add MCP Server in ChatGPT settings:"
    cat <<EOF

Server Name: Ministry Data
Server URL: ${SERVICE_URL}/sse
Authentication: Bearer Token
Token: ${MCP_BEARER_TOKEN}
EOF

    echo -e "\n${YELLOW}2. For curl testing (standard MCP SSE protocol):${NC}"
    cat <<EOF

# Step 1: Establish SSE connection (GET /sse)
curl -N \\
  -H "Authorization: Bearer ${MCP_BEARER_TOKEN}" \\
  -H "Accept: text/event-stream" \\
  "${SERVICE_URL}/sse" &
SSE_PID=\$!

# Step 2: Send initialize message (POST /sse)
sleep 1
curl -X POST \\
  -H "Authorization: Bearer ${MCP_BEARER_TOKEN}" \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \\
  "${SERVICE_URL}/sse"

# Step 3: Send list tools message
curl -X POST \\
  -H "Authorization: Bearer ${MCP_BEARER_TOKEN}" \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \\
  "${SERVICE_URL}/sse"

# Cleanup
kill \$SSE_PID 2>/dev/null || true
EOF

    echo -e "\n${YELLOW}3. Note: Standard MCP clients (e.g., @modelcontextprotocol/sdk)${NC}"
    echo "   will automatically handle GET/POST SSE protocol."

    echo -e "\n${YELLOW}4. Save your Bearer Token securely:${NC}"
    echo "   Token: ${MCP_BEARER_TOKEN}"
    echo "   (Store this in a password manager)"
else
    echo -e "${RED}Warning: Service deployed without authentication (or token not available locally)!${NC}"
    echo "If you created a secret, check Secret Manager for the token."
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
