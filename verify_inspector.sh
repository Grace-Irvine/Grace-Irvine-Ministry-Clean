#!/bin/bash
# 验证 MCP Inspector 连接状态

echo "🔍 检查 MCP Inspector 状态..."
echo ""

# 1. 检查进程
echo "1️⃣ 检查进程："
if pgrep -f "@modelcontextprotocol/inspector" > /dev/null; then
    echo "   ✅ Inspector 正在运行"
    echo "   进程列表："
    ps aux | grep -E 'inspector|mcp_cloud_proxy' | grep -v grep | sed 's/^/      /'
else
    echo "   ❌ Inspector 未运行"
    echo "   请运行: bash inspect_cloud_mcp.sh"
fi
echo ""

# 2. 检查端口
echo "2️⃣ 检查端口："
for port in 6274 6277; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "   ✅ 端口 $port 正在使用"
    else
        echo "   ⚠️  端口 $port 未使用"
    fi
done
echo ""

# 3. 检查代理
echo "3️⃣ 检查代理连接："
if pgrep -f "mcp_cloud_proxy.py" > /dev/null; then
    echo "   ✅ 代理进程运行中"
else
    echo "   ⚠️  代理进程未运行"
fi
echo ""

# 4. 测试服务器
echo "4️⃣ 测试云端服务器："
HEALTH=$(curl -s -H "Authorization: Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30" \
    "https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/health" 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "   ✅ 服务器健康"
    echo "   状态: $(echo $HEALTH | jq -r .status 2>/dev/null || echo 'unknown')"
else
    echo "   ❌ 服务器连接失败"
fi
echo ""

# 5. Inspector URL
echo "5️⃣ Inspector 访问地址："
if pgrep -f "@modelcontextprotocol/inspector" > /dev/null; then
    echo "   🌐 http://localhost:6274"
    echo ""
    echo "   💡 在浏览器中打开上面的地址"
    echo "   💡 左侧应该显示 'ministry-data-cloud' 服务器"
else
    echo "   ⚠️  Inspector 未运行"
fi
echo ""

# 总结
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if pgrep -f "@modelcontextprotocol/inspector" > /dev/null && [ ! -z "$HEALTH" ]; then
    echo "✅ 一切正常！在浏览器中访问 http://localhost:6274"
    echo ""
    echo "📝 使用提示："
    echo "   1. 左侧找到 'ministry-data-cloud' 服务器"
    echo "   2. 点击展开，查看 Tools、Resources、Prompts"
    echo "   3. 不要在 UI 中手动添加 SSE 连接！"
else
    echo "⚠️  有问题，请运行: bash inspect_cloud_mcp.sh"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

