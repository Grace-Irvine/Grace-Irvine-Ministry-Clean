#!/bin/bash
# Test script for unified MCP server
# Tests both stdio and HTTP modes

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Testing Unified MCP Server${NC}"
echo -e "${GREEN}========================================${NC}"

cd "$(dirname "$0")"

# Test 1: Check file exists
echo -e "\n${YELLOW}[1/4] Checking file structure...${NC}"
if [ -f "mcp_local/mcp_server.py" ]; then
    echo -e "${GREEN}✓ mcp_server.py exists${NC}"
else
    echo -e "${RED}✗ mcp_server.py not found${NC}"
    exit 1
fi

if [ -f "mcp_local/mcp_http_server.py" ]; then
    echo -e "${RED}✗ Old mcp_http_server.py still exists (should be deleted)${NC}"
    exit 1
else
    echo -e "${GREEN}✓ mcp_http_server.py deleted${NC}"
fi

# Test 2: Check imports
echo -e "\n${YELLOW}[2/4] Checking imports...${NC}"
if grep -q "from fastapi import FastAPI" mcp_local/mcp_server.py; then
    echo -e "${GREEN}✓ FastAPI imports present${NC}"
else
    echo -e "${RED}✗ FastAPI imports missing${NC}"
    exit 1
fi

if grep -q "from mcp.server.stdio import stdio_server" mcp_local/mcp_server.py; then
    echo -e "${GREEN}✓ stdio imports present${NC}"
else
    echo -e "${RED}✗ stdio imports missing${NC}"
    exit 1
fi

# Test 3: Check mode detection logic
echo -e "\n${YELLOW}[3/4] Checking mode detection logic...${NC}"
if grep -q 'if os.getenv("PORT") or "--http" in sys.argv:' mcp_local/mcp_server.py; then
    echo -e "${GREEN}✓ Mode detection logic present${NC}"
else
    echo -e "${RED}✗ Mode detection logic missing${NC}"
    exit 1
fi

# Test 4: Check Dockerfile
echo -e "\n${YELLOW}[4/4] Checking Dockerfile...${NC}"
if grep -q "mcp_local/mcp_server.py" mcp_local/Dockerfile; then
    echo -e "${GREEN}✓ Dockerfile uses unified server${NC}"
else
    echo -e "${RED}✗ Dockerfile not updated${NC}"
    exit 1
fi

if grep -q "mcp_http_server.py" mcp_local/Dockerfile; then
    echo -e "${RED}✗ Dockerfile still references old file${NC}"
    exit 1
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}All checks passed!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}Manual Testing:${NC}"
echo -e "1. stdio mode: ${GREEN}python mcp_local/mcp_server.py${NC}"
echo -e "2. HTTP mode:  ${GREEN}PORT=8080 python mcp_local/mcp_server.py${NC}"
echo -e "3. HTTP test:  ${GREEN}curl http://localhost:8080/health${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Test locally in stdio mode with Claude Desktop"
echo "2. Test locally in HTTP mode: PORT=8080 python mcp_local/mcp_server.py"
echo "3. Test with ngrok for OpenAI ChatGPT"
echo "4. Deploy to Cloud Run: ./deploy/deploy-mcp.sh"

