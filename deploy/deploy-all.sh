#!/bin/bash
# 统一部署脚本 - 部署API服务和MCP服务
# 按顺序部署两个独立的Cloud Run服务

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Ministry Data Services Deployment${NC}"
echo -e "${BLUE}部署API服务和MCP服务到Google Cloud Run${NC}"
echo -e "${BLUE}============================================${NC}"

# 检查必需的环境变量
if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID is not set${NC}"
    echo "Usage: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

echo -e "\n${GREEN}环境配置:${NC}"
echo "  GCP Project: $GCP_PROJECT_ID"
echo "  GCP Region: ${GCP_REGION:-us-central1}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}[1/2] 部署 API 服务${NC}"
echo -e "${BLUE}============================================${NC}"

cd "$PROJECT_ROOT"
bash "$SCRIPT_DIR/deploy-api.sh"

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ API服务部署成功${NC}"
else
    echo -e "\n${RED}✗ API服务部署失败${NC}"
    exit 1
fi

echo -e "\n${BLUE}============================================${NC}"
echo -e "${BLUE}[2/2] 部署 MCP 服务${NC}"
echo -e "${BLUE}============================================${NC}"

bash "$SCRIPT_DIR/deploy-mcp.sh"

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ MCP服务部署成功${NC}"
else
    echo -e "\n${RED}✗ MCP服务部署失败${NC}"
    exit 1
fi

echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"

echo -e "\n${YELLOW}已部署的服务:${NC}"
echo -e "  1. ${GREEN}API服务${NC} - ministry-data-api"
echo -e "     提供数据清洗和管理API"
echo -e ""
echo -e "  2. ${GREEN}MCP服务${NC} - ministry-data-mcp"
echo -e "     提供AI助手集成（MCP协议）"
echo -e ""

echo -e "${YELLOW}下一步:${NC}"
echo "  1. 查看API文档: https://ministry-data-api-<hash>.run.app/docs"
echo "  2. 查看MCP能力: https://ministry-data-mcp-<hash>.run.app/mcp/capabilities"
echo "  3. 测试健康检查:"
echo "     curl https://ministry-data-api-<hash>.run.app/health"
echo "     curl https://ministry-data-mcp-<hash>.run.app/health"
echo ""

echo -e "${BLUE}============================================${NC}"

