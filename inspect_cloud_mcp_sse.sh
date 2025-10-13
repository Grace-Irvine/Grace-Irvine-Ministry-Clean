#!/bin/bash
# MCP Inspector for Cloud Run - SSE Direct Connection
# 直接使用 SSE 连接（不通过代理）

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MCP Inspector - SSE Direct Mode${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# MCP 服务器配置
MCP_URL="${MCP_URL:-https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app}"
MCP_TOKEN="${MCP_TOKEN:-db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30}"

echo -e "${BLUE}Service URL:${NC} $MCP_URL"
echo -e "${BLUE}SSE Endpoint:${NC} $MCP_URL/mcp/sse"
echo -e "${BLUE}Transport:${NC} SSE (Server-Sent Events)"
echo -e "${BLUE}Auth:${NC} Bearer Token"
echo ""

# 检查健康状态
echo -e "${YELLOW}Checking server health...${NC}"
HEALTH_CHECK=$(curl -s -H "Authorization: Bearer $MCP_TOKEN" "$MCP_URL/health")
if [ $? -ne 0 ]; then
  echo -e "${RED}✗ Cannot connect to server${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Server Status:${NC} $HEALTH_CHECK"
echo ""

# 测试 SSE 端点
echo -e "${YELLOW}Testing SSE endpoint...${NC}"
SSE_TEST=$(curl -s -I -H "Authorization: Bearer $MCP_TOKEN" -H "Accept: text/event-stream" "$MCP_URL/mcp/sse")
if echo "$SSE_TEST" | grep -q "404"; then
  echo -e "${RED}✗ SSE endpoint not available (404)${NC}"
  echo -e "${YELLOW}Note: Your server may not support SSE transport.${NC}"
  echo -e "${YELLOW}Please use the stdio proxy mode instead: ./inspect_cloud_mcp.sh${NC}"
  exit 1
fi
echo -e "${GREEN}✓ SSE endpoint available${NC}"
echo ""

# 创建临时配置文件（使用 SSE）
TEMP_CONFIG=$(mktemp)
cat > "$TEMP_CONFIG" << EOF
{
  "mcpServers": {
    "ministry-data-cloud-sse": {
      "url": "$MCP_URL/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer $MCP_TOKEN"
      }
    }
  }
}
EOF

echo -e "${YELLOW}Using SSE transport (direct connection)${NC}"
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

# 清理可能占用端口的旧进程
cleanup_ports() {
  echo -e "${YELLOW}Cleaning up ports 6274 and 6277...${NC}"
  for port in 6274 6277; do
    PID=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$PID" ]; then
      echo -e "${YELLOW}Killing process $PID using port $port${NC}"
      kill -9 $PID 2>/dev/null || true
      sleep 0.5
    fi
  done
}

# 设置清理函数
cleanup() {
  echo ""
  echo -e "${YELLOW}Shutting down...${NC}"
  cleanup_ports
  rm -f "$TEMP_CONFIG"
}

# 在退出时清理
trap cleanup EXIT INT TERM

# 启动前先清理可能的旧进程
cleanup_ports

# 启动 MCP Inspector with SSE
npx -y @modelcontextprotocol/inspector --config "$TEMP_CONFIG"

