#!/bin/bash
# Secret Manager 设置脚本
# 创建所有必需的 secrets 并授予 Cloud Run 服务账号访问权限

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Secret Manager 设置${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查必需的环境变量
if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID is not set${NC}"
    echo "Usage: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

PROJECT_ID="$GCP_PROJECT_ID"

# 设置项目
gcloud config set project "$PROJECT_ID"

# 启用 Secret Manager API
echo -e "\n${GREEN}[1/4] 启用 Secret Manager API...${NC}"
gcloud services enable secretmanager.googleapis.com || true
echo -e "${GREEN}✓ Secret Manager API 已启用${NC}"

# Cloud Run 默认服务账号
CLOUD_RUN_SA="${PROJECT_ID}@appspot.gserviceaccount.com"

# 定义所有需要的 secrets (使用数组，索引为 secret 名称，值为描述)
SECRET_NAMES=("mcp-bearer-token" "api-scheduler-token")
SECRET_DESCS=("MCP Bearer Token for authentication" "API Scheduler Token for Cloud Scheduler")

echo -e "\n${GREEN}[2/4] 创建或更新 Secrets...${NC}"

# 创建或更新每个 secret
for i in "${!SECRET_NAMES[@]}"; do
    SECRET_NAME="${SECRET_NAMES[$i]}"
    SECRET_DESC="${SECRET_DESCS[$i]}"
    
    # 检查 secret 是否存在
    if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &> /dev/null; then
        echo -e "  ${GREEN}Secret '$SECRET_NAME' 已存在${NC}"
        # 非交互模式：跳过更新（如果环境变量 FORCE_UPDATE 未设置）
        if [ "${FORCE_UPDATE_SECRETS:-false}" = "true" ]; then
            # 生成新的 token
            TOKEN=$(openssl rand -hex 32)
            echo -n "$TOKEN" | gcloud secrets versions add "$SECRET_NAME" --data-file=-
            echo -e "  ${GREEN}✓ Secret '$SECRET_NAME' 已更新${NC}"
            echo -e "  ${YELLOW}  新 Token: $TOKEN${NC}"
            echo -e "  ${YELLOW}  (请保存此 token 以备后续使用)${NC}"
        else
            echo -e "  ${GREEN}✓ 跳过更新 '$SECRET_NAME'（如需更新，设置 FORCE_UPDATE_SECRETS=true）${NC}"
        fi
    else
        # 创建新的 secret
        echo -e "  创建 secret: ${YELLOW}$SECRET_NAME${NC}"
        TOKEN=$(openssl rand -hex 32)
        echo -n "$TOKEN" | gcloud secrets create "$SECRET_NAME" \
            --data-file=- \
            --replication-policy="automatic" \
            --project="$PROJECT_ID"
        echo -e "  ${GREEN}✓ Secret '$SECRET_NAME' 已创建${NC}"
        echo -e "  ${YELLOW}  Token: $TOKEN${NC}"
        echo -e "  ${YELLOW}  (请保存此 token 以备后续使用)${NC}"
    fi
done

echo -e "\n${GREEN}[3/4] 授予服务账号访问权限...${NC}"

# 为每个 secret 授予 Cloud Run 服务账号访问权限
for i in "${!SECRET_NAMES[@]}"; do
    SECRET_NAME="${SECRET_NAMES[$i]}"
    echo -e "  配置 '$SECRET_NAME' 的访问权限..."
    
    # 授予 Cloud Run 默认服务账号访问权限
    gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
        --member="serviceAccount:${CLOUD_RUN_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --project="$PROJECT_ID" \
        --quiet || true
    
    echo -e "  ${GREEN}✓ '$SECRET_NAME' 访问权限已配置${NC}"
done

echo -e "\n${GREEN}[4/4] 验证 Secrets 设置...${NC}"

# 验证所有 secrets 都存在
ALL_EXIST=true
for i in "${!SECRET_NAMES[@]}"; do
    SECRET_NAME="${SECRET_NAMES[$i]}"
    if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &> /dev/null; then
        echo -e "  ${GREEN}✓ '$SECRET_NAME' 存在${NC}"
    else
        echo -e "  ${RED}✗ '$SECRET_NAME' 不存在${NC}"
        ALL_EXIST=false
    fi
done

if [ "$ALL_EXIST" = true ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}Secret Manager 设置完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}已创建的 Secrets:${NC}"
    for i in "${!SECRET_NAMES[@]}"; do
        SECRET_NAME="${SECRET_NAMES[$i]}"
        SECRET_DESC="${SECRET_DESCS[$i]}"
        echo -e "  - ${GREEN}$SECRET_NAME${NC}: $SECRET_DESC"
    done
    echo ""
    echo -e "${YELLOW}注意事项:${NC}"
    echo "  1. Cloud Run 服务账号已获得访问权限"
    echo "  2. 代码会自动从 Secret Manager 读取 secrets"
    echo "  3. 如需更新 secret，运行: gcloud secrets versions add SECRET_NAME --data-file=-"
else
    echo -e "\n${RED}某些 secrets 设置失败，请检查错误信息${NC}"
    exit 1
fi

