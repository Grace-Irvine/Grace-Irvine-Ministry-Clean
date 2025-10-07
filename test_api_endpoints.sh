#!/bin/bash
# 测试 API 端点
# 用法：./test_api_endpoints.sh [SERVICE_URL]
# 示例：./test_api_endpoints.sh https://your-service.run.app

BASE_URL="${1:-http://localhost:8080}"

echo "============================================================"
echo "测试 API 端点"
echo "============================================================"
echo ""
echo "基础 URL: $BASE_URL"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试函数
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo "测试: $description"
    echo "端点: $method $endpoint"
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ $http_code -ge 200 ] && [ $http_code -lt 300 ]; then
        echo -e "${GREEN}✅ 成功 (HTTP $http_code)${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ 失败 (HTTP $http_code)${NC}"
        echo "$body"
    fi
    
    echo ""
    echo "------------------------------------------------------------"
    echo ""
}

# 开始测试
echo "============================================================"
echo "1. 健康检查"
echo "============================================================"
test_endpoint "GET" "/health" "" "健康检查"

echo "============================================================"
echo "2. API 端点测试"
echo "============================================================"

test_endpoint "GET" "/api/v1/stats" "" "获取统计信息"

test_endpoint "POST" "/api/v1/query" '{"limit": 5}' "查询数据（前 5 条）"

test_endpoint "POST" "/api/v1/query" '{
  "date_from": "2025-01-01",
  "limit": 3
}' "按日期查询"

test_endpoint "POST" "/api/v1/clean" '{"dry_run": true}' "触发清洗（dry-run）"

echo "============================================================"
echo "3. MCP 端点测试"
echo "============================================================"

test_endpoint "GET" "/mcp/tools" "" "获取 MCP 工具定义"

echo "============================================================"
echo "测试完成"
echo "============================================================"
echo ""
echo "提示："
echo "- 查看完整 API 文档: $BASE_URL/docs"
echo "- 使用 ReDoc: $BASE_URL/redoc"
echo ""

