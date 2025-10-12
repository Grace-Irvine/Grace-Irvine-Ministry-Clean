#!/bin/bash
# MCP Inspector for Cloud Run Deployment
# 连接到部署在 Google Cloud Run 上的 MCP 服务器

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MCP Inspector - Cloud Run${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# MCP 服务器配置
MCP_URL="${MCP_URL:-https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app}"
MCP_TOKEN="${MCP_TOKEN:-db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30}"

echo -e "${BLUE}Service URL:${NC} $MCP_URL"
echo -e "${BLUE}Transport:${NC} SSE (Server-Sent Events)"
echo -e "${BLUE}Auth:${NC} Bearer Token"
echo ""

# 检查健康状态
echo -e "${YELLOW}Checking server health...${NC}"
HEALTH_CHECK=$(curl -s -H "Authorization: Bearer $MCP_TOKEN" "$MCP_URL/health")
echo -e "${GREEN}✓ Server Status:${NC} $HEALTH_CHECK"
echo ""

# 创建临时配置文件
TEMP_CONFIG=$(mktemp)
cat > "$TEMP_CONFIG" << EOF
{
  "mcpServers": {
    "ministry-data-cloud": {
      "url": "$MCP_URL/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer $MCP_TOKEN"
      }
    }
  }
}
EOF

echo -e "${YELLOW}Configuration saved to:${NC} $TEMP_CONFIG"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Opening MCP Inspector...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "The MCP Inspector will open in your browser."
echo -e "You can interact with the following endpoints:"
echo ""
echo -e "  ${BLUE}Tools:${NC}     /mcp/tools"
echo -e "  ${BLUE}Resources:${NC} /mcp/resources"
echo -e "  ${BLUE}Prompts:${NC}   /mcp/prompts"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# 启动 MCP Inspector
# 注意：MCP Inspector 需要通过配置文件或命令行参数来连接 SSE 服务器
npx -y @modelcontextprotocol/inspector --config "$TEMP_CONFIG"

# 清理临时文件
trap "rm -f $TEMP_CONFIG" EXIT

