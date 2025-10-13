#!/bin/bash
# 停止 MCP Inspector 进程并释放端口
# Stop MCP Inspector processes and free up ports

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Stopping MCP Inspector processes...${NC}"
echo ""

# 清理 MCP Inspector 使用的端口
PORTS=(6274 6277)
KILLED=0

for port in "${PORTS[@]}"; do
  PID=$(lsof -ti:$port 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo -e "${YELLOW}Found process $PID using port $port${NC}"
    kill -9 $PID 2>/dev/null || true
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}✓ Killed process $PID (port $port)${NC}"
      KILLED=$((KILLED + 1))
    else
      echo -e "${RED}✗ Failed to kill process $PID${NC}"
    fi
  fi
done

# 检查是否还有其他 MCP Inspector 进程
MCP_PROCS=$(ps aux | grep -E 'mcp.*inspector|npx.*@modelcontextprotocol' | grep -v grep | awk '{print $2}')
if [ -n "$MCP_PROCS" ]; then
  echo ""
  echo -e "${YELLOW}Found additional MCP Inspector processes:${NC}"
  echo "$MCP_PROCS" | while read pid; do
    echo -e "${YELLOW}  Killing process $pid${NC}"
    kill -9 $pid 2>/dev/null || true
    KILLED=$((KILLED + 1))
  done
fi

echo ""
if [ $KILLED -gt 0 ]; then
  echo -e "${GREEN}✓ Stopped $KILLED process(es)${NC}"
else
  echo -e "${GREEN}✓ No MCP Inspector processes found${NC}"
fi

# 验证端口已释放
echo ""
echo -e "${YELLOW}Verifying ports are free...${NC}"
ALL_FREE=true
for port in "${PORTS[@]}"; do
  PID=$(lsof -ti:$port 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo -e "${RED}✗ Port $port still in use by process $PID${NC}"
    ALL_FREE=false
  else
    echo -e "${GREEN}✓ Port $port is free${NC}"
  fi
done

echo ""
if [ "$ALL_FREE" = true ]; then
  echo -e "${GREEN}All ports are now available!${NC}"
  echo -e "You can now start MCP Inspector with: ${YELLOW}./inspect_cloud_mcp.sh${NC}"
else
  echo -e "${RED}Some ports are still in use. You may need to manually kill the processes.${NC}"
fi

