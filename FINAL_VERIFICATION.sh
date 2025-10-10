#!/bin/bash

echo "=================================================="
echo "🧪 OpenAI Apps SDK 最终验证"
echo "=================================================="
echo ""

NGROK_URL="https://2e3dfdd56609.ngrok-free.app"

echo "1️⃣  测试健康检查..."
HEALTH=$(curl -s $NGROK_URL/health | python3 -c "import json, sys; print(json.load(sys.stdin)['status'])")
if [ "$HEALTH" = "healthy" ]; then
    echo "   ✅ 健康检查通过"
else
    echo "   ❌ 健康检查失败"
    exit 1
fi

echo ""
echo "2️⃣  测试 MCP 初始化..."
INIT=$(curl -s -X POST $NGROK_URL/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | \
  python3 -c "import json, sys; d=json.load(sys.stdin); print(d['result']['serverInfo']['name'])")
if [ "$INIT" = "ministry-data" ]; then
    echo "   ✅ 初始化成功"
else
    echo "   ❌ 初始化失败"
    exit 1
fi

echo ""
echo "3️⃣  测试工具列表..."
TOOLS_COUNT=$(curl -s -X POST $NGROK_URL/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | \
  python3 -c "import json, sys; print(len(json.load(sys.stdin)['result']['tools']))")
echo "   ✅ 找到 $TOOLS_COUNT 个工具"

echo ""
echo "4️⃣  测试工具元数据..."
HAS_META=$(curl -s -X POST $NGROK_URL/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/list"}' | \
  python3 -c "import json, sys; tools=json.load(sys.stdin)['result']['tools']; print(all('meta' in t for t in tools))")
if [ "$HAS_META" = "True" ]; then
    echo "   ✅ 所有工具都有 meta 字段"
else
    echo "   ❌ 部分工具缺少 meta 字段"
    exit 1
fi

echo ""
echo "5️⃣  测试工具调用..."
HAS_STRUCTURED=$(curl -s -X POST $NGROK_URL/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "query_volunteers_by_date",
      "arguments": {"date": "2025-10-12"}
    }
  }' | python3 -c "import json, sys; d=json.load(sys.stdin); c=d['result']['content'][0]; print('structuredContent' in c)")

if [ "$HAS_STRUCTURED" = "True" ]; then
    echo "   ✅ 工具调用成功"
    echo "   ✅ 响应格式正确（含 structuredContent）"
else
    echo "   ❌ 响应格式错误"
    exit 1
fi

echo ""
echo "=================================================="
echo "🎉 所有测试通过！"
echo "=================================================="
echo ""
echo "📍 您的 MCP 端点 URL:"
echo "   $NGROK_URL/mcp"
echo ""
echo "📖 下一步:"
echo "   1. 打开 https://chat.openai.com"
echo "   2. Settings → Connectors → Create"
echo "   3. 粘贴上方 URL"
echo "   4. 开始对话！"
echo ""
echo "📚 详细指南:"
echo "   - QUICK_START_CHATGPT.md (快速开始)"
echo "   - CHATGPT_CONNECTION_GUIDE.md (完整指南)"
echo ""
