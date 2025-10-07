#!/bin/bash
# 本地测试 MCP Server

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MCP Server Local Testing${NC}"
echo -e "${GREEN}========================================${NC}"

# 测试模式选择
echo "Select test mode:"
echo "1) stdio mode (for local Claude Desktop)"
echo "2) HTTP mode (for remote deployment)"
read -p "Enter choice (1 or 2): " MODE

if [ "$MODE" = "1" ]; then
    echo -e "\n${GREEN}Starting MCP Server in stdio mode...${NC}"
    echo "This will start an interactive MCP session."
    echo "Press Ctrl+C to exit."
    echo ""
    python3 mcp_server.py

elif [ "$MODE" = "2" ]; then
    echo -e "\n${GREEN}Starting MCP HTTP Server...${NC}"
    
    # 设置测试 token
    export MCP_BEARER_TOKEN=${MCP_BEARER_TOKEN:-"test-token-12345"}
    export MCP_REQUIRE_AUTH=${MCP_REQUIRE_AUTH:-"false"}
    export PORT=8080
    
    echo "Server will start on http://localhost:8080"
    echo "Bearer Token: $MCP_BEARER_TOKEN"
    echo "Auth Required: $MCP_REQUIRE_AUTH"
    echo ""
    echo "Test endpoints:"
    echo "  - http://localhost:8080/health"
    echo "  - http://localhost:8080/mcp/capabilities"
    echo "  - http://localhost:8080/mcp/tools"
    echo ""
    echo "Press Ctrl+C to stop."
    echo ""
    
    python3 mcp_http_server.py

else
    echo "Invalid choice"
    exit 1
fi

