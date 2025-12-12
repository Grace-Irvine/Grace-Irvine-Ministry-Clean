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

# 配置参数
REGION="${GCP_REGION:-us-central1}"
API_SERVICE_NAME="ministry-data-cleaning"
MCP_SERVICE_NAME="${MCP_SERVICE_NAME:-ministry-data-mcp}"

echo -e "\n${GREEN}环境配置:${NC}"
echo "  GCP Project: $GCP_PROJECT_ID"
echo "  GCP Region: $REGION"
echo "  API Service: $API_SERVICE_NAME"
echo "  MCP Service: $MCP_SERVICE_NAME"
echo "  Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# 记录开始时间
START_TIME=$(date +%s)

# ============================================
# 部署 API 服务
# ============================================
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}[1/2] 部署 API 服务${NC}"
echo -e "${BLUE}============================================${NC}"

cd "$PROJECT_ROOT"

# 执行 API 部署
if bash "$SCRIPT_DIR/deploy-api.sh"; then
    echo -e "\n${GREEN}✓ API服务部署成功${NC}"

    # 获取 API 服务 URL
    API_URL=$(gcloud run services describe "$API_SERVICE_NAME" \
        --region "$REGION" \
        --format 'value(status.url)' 2>/dev/null || echo "")

    if [ -n "$API_URL" ]; then
        echo -e "  URL: ${YELLOW}${API_URL}${NC}"
    fi
else
    echo -e "\n${RED}✗ API服务部署失败${NC}"
    exit 1
fi

# ============================================
# 部署 MCP 服务
# ============================================
echo -e "\n${BLUE}============================================${NC}"
echo -e "${BLUE}[2/2] 部署 MCP 服务${NC}"
echo -e "${BLUE}============================================${NC}"

# 执行 MCP 部署
if bash "$SCRIPT_DIR/deploy-mcp.sh"; then
    echo -e "\n${GREEN}✓ MCP服务部署成功${NC}"

    # 获取 MCP 服务 URL
    MCP_URL=$(gcloud run services describe "$MCP_SERVICE_NAME" \
        --region "$REGION" \
        --format 'value(status.url)' 2>/dev/null || echo "")

    if [ -n "$MCP_URL" ]; then
        echo -e "  URL: ${YELLOW}${MCP_URL}${NC}"
    fi
else
    echo -e "\n${RED}✗ MCP服务部署失败${NC}"
    exit 1
fi

# ============================================
# 部署完成总结
# ============================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e "总耗时: ${MINUTES}分${SECONDS}秒"
echo -e "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"

echo -e "\n${YELLOW}已部署的服务:${NC}"
echo -e "  1. ${GREEN}API服务${NC} - $API_SERVICE_NAME"
echo -e "     提供数据清洗和管理API"
if [ -n "$API_URL" ]; then
    echo -e "     URL: ${YELLOW}${API_URL}${NC}"
    echo -e "     文档: ${YELLOW}${API_URL}/docs${NC}"
    echo -e "     健康检查: ${YELLOW}${API_URL}/health${NC}"
fi
echo -e ""
echo -e "  2. ${GREEN}MCP服务${NC} - $MCP_SERVICE_NAME"
echo -e "     提供AI助手集成（MCP协议）"
if [ -n "$MCP_URL" ]; then
    echo -e "     URL: ${YELLOW}${MCP_URL}${NC}"
    echo -e "     MCP端点(HTTP/SSE): ${YELLOW}${MCP_URL}/mcp${NC}"
    echo -e "     兼容端点(legacy): ${YELLOW}${MCP_URL}/sse${NC}"
    echo -e "     健康检查: ${YELLOW}${MCP_URL}/health${NC}"
fi
echo -e ""

# 验证服务状态
echo -e "${YELLOW}验证服务状态:${NC}"
if [ -n "$API_URL" ]; then
    echo -e "  API服务:"
    API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health" 2>/dev/null || echo "000")
    if [ "$API_HEALTH" = "200" ]; then
        echo -e "    ${GREEN}✓ 健康检查通过 (HTTP $API_HEALTH)${NC}"
    else
        echo -e "    ${YELLOW}⚠ 健康检查异常 (HTTP $API_HEALTH)${NC}"
    fi
fi

if [ -n "$MCP_URL" ]; then
    echo -e "  MCP服务:"
    MCP_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$MCP_URL/health" 2>/dev/null || echo "000")
    if [ "$MCP_HEALTH" = "200" ]; then
        echo -e "    ${GREEN}✓ 健康检查通过 (HTTP $MCP_HEALTH)${NC}"
    else
        echo -e "    ${YELLOW}⚠ 健康检查异常 (HTTP $MCP_HEALTH)${NC}"
    fi
fi

echo -e "\n${YELLOW}下一步:${NC}"
if [ -n "$API_URL" ]; then
    echo -e "  1. 测试API服务:"
    echo -e "     curl ${API_URL}/health"
    echo -e "     curl -X POST \"${API_URL}/api/v1/clean\" -H \"Content-Type: application/json\" -d '{\"dry_run\": true}'"
fi
if [ -n "$MCP_URL" ]; then
    echo -e "  2. 配置OpenAI ChatGPT MCP集成:"
    echo -e "     Server URL: ${MCP_URL}/mcp"
    echo -e "     (需要Bearer Token进行认证)"
fi
echo -e "  3. 查看Cloud Run控制台:"
echo -e "     https://console.cloud.google.com/run?project=${GCP_PROJECT_ID}"
echo ""

echo -e "${BLUE}============================================${NC}"

