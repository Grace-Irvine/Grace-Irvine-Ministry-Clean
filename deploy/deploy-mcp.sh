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
    echo "Generate a secure token with: openssl rand -hex 32"
    read -p "Enter Bearer Token (or press Enter to skip): " MCP_BEARER_TOKEN
    if [ -z "$MCP_BEARER_TOKEN" ]; then
        echo -e "${YELLOW}Deploying without authentication...${NC}"
    fi
fi

# 配置参数
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${MCP_SERVICE_NAME:-ministry-data-mcp}"
IMAGE_NAME="gcr.io/${GCP_PROJECT_ID}/${SERVICE_NAME}"
DOCKERFILE_PATH="mcp/Dockerfile"
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

# 确认部署
read -p "Continue with deployment? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
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
    containerregistry.googleapis.com
echo -e "${GREEN}✓ APIs enabled${NC}"

# 3. 构建 Docker 镜像
echo -e "\n${GREEN}[3/6] Building Docker image...${NC}"
echo "  Using Dockerfile: $DOCKERFILE_PATH"
gcloud builds submit \
    --tag $IMAGE_NAME \
    --file=$DOCKERFILE_PATH \
    --timeout=10m
echo -e "${GREEN}✓ Image built: $IMAGE_NAME${NC}"

# 4. 部署到 Cloud Run
echo -e "\n${GREEN}[4/6] Deploying to Cloud Run...${NC}"

DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --memory $MEMORY \
    --cpu $CPU \
    --timeout $TIMEOUT \
    --max-instances $MAX_INSTANCES \
    --min-instances $MIN_INSTANCES \
    --set-env-vars MCP_MODE=http,MCP_REQUIRE_AUTH=true \
    --allow-unauthenticated"

# 构建 secrets 列表
SECRETS_LIST=""

# 添加 Bearer Token（如果设置）
if [ -n "$MCP_BEARER_TOKEN" ]; then
    SECRETS_LIST="MCP_BEARER_TOKEN=mcp-bearer-token:latest"
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
eval $DEPLOY_CMD
echo -e "${GREEN}✓ Service deployed${NC}"

# 5. 创建或更新 Secret（如果提供了 Token）
if [ -n "$MCP_BEARER_TOKEN" ]; then
    echo -e "\n${GREEN}[5/6] Setting up Bearer Token secret...${NC}"
    
    # 检查 secret 是否存在
    if gcloud secrets describe mcp-bearer-token --project=$GCP_PROJECT_ID &> /dev/null 2>&1; then
        echo "  Secret exists, updating..."
        echo -n "$MCP_BEARER_TOKEN" | gcloud secrets versions add mcp-bearer-token --data-file=-
    else
        echo "  Creating new secret..."
        echo -n "$MCP_BEARER_TOKEN" | gcloud secrets create mcp-bearer-token --data-file=-
    fi
    
    # 授予 Cloud Run 访问权限
    gcloud secrets add-iam-policy-binding mcp-bearer-token \
        --member="serviceAccount:${GCP_PROJECT_ID}@appspot.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
    
    echo -e "${GREEN}✓ Bearer Token secret configured${NC}"
else
    echo -e "\n${YELLOW}[5/6] Skipping Bearer Token setup (not provided)${NC}"
fi

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
echo -e "  - Capabilities: ${YELLOW}${SERVICE_URL}/mcp/capabilities${NC}"
echo -e "  - Tools: ${YELLOW}${SERVICE_URL}/mcp/tools${NC}"
echo -e "  - Resources: ${YELLOW}${SERVICE_URL}/mcp/resources${NC}"
echo -e "  - Prompts: ${YELLOW}${SERVICE_URL}/mcp/prompts${NC}"
echo -e "  - SSE: ${YELLOW}${SERVICE_URL}/mcp/sse${NC}"
echo ""

# 测试健康检查
echo -e "${GREEN}Testing health endpoint...${NC}"
if [ -n "$MCP_BEARER_TOKEN" ]; then
    HEALTH_RESPONSE=$(curl -s -H "Authorization: Bearer $MCP_BEARER_TOKEN" "${SERVICE_URL}/health")
else
    HEALTH_RESPONSE=$(curl -s "${SERVICE_URL}/health")
fi
echo -e "Health: ${YELLOW}${HEALTH_RESPONSE}${NC}"

# 生成客户端配置
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Client Configuration${NC}"
echo -e "${GREEN}========================================${NC}"

if [ -n "$MCP_BEARER_TOKEN" ]; then
    echo -e "\n${YELLOW}1. For Claude Desktop (macOS/Linux):${NC}"
    echo "   Add to ~/.config/Claude/claude_desktop_config.json:"
    cat <<EOF

{
  "mcpServers": {
    "ministry-data": {
      "url": "${SERVICE_URL}/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer ${MCP_BEARER_TOKEN}"
      }
    }
  }
}
EOF

    echo -e "\n${YELLOW}2. For curl testing:${NC}"
    cat <<EOF

# List tools
curl -X POST "${SERVICE_URL}/mcp" \\
  -H "Authorization: Bearer ${MCP_BEARER_TOKEN}" \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'

# List resources
curl -X POST "${SERVICE_URL}/mcp" \\
  -H "Authorization: Bearer ${MCP_BEARER_TOKEN}" \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc": "2.0", "id": 2, "method": "resources/list"}'
EOF

    echo -e "\n${YELLOW}3. Save your Bearer Token securely:${NC}"
    echo "   Token: ${MCP_BEARER_TOKEN}"
    echo "   (Store this in a password manager)"
else
    echo -e "${RED}Warning: Service deployed without authentication!${NC}"
    echo "For production use, set MCP_BEARER_TOKEN and redeploy."
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"

