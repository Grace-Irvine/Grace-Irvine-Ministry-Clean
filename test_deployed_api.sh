#!/bin/bash
# 测试已部署的 Cloud Run API

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 服务 URL
SERVICE_URL="${SERVICE_URL:-https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app}"

print_test() {
    echo -e "${YELLOW}[测试]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

echo "======================================"
echo "  测试 Cloud Run API 端点"
echo "======================================"
echo "服务 URL: $SERVICE_URL"
echo ""

# 测试 1: 健康检查
print_test "1. 健康检查端点"
response=$(curl -s "${SERVICE_URL}/health")
if echo "$response" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    print_success "健康检查通过"
    echo "$response" | jq .
else
    print_error "健康检查失败"
    echo "$response"
    exit 1
fi
echo ""

# 测试 2: MCP 工具定义
print_test "2. MCP 工具定义端点"
response=$(curl -s "${SERVICE_URL}/mcp/tools")
tool_count=$(echo "$response" | jq -r '.tools | length')
if [ "$tool_count" -ge 3 ]; then
    print_success "MCP 工具定义正常 (找到 ${tool_count} 个工具)"
    echo "$response" | jq '.tools[] | .name'
else
    print_error "MCP 工具定义异常"
    echo "$response"
    exit 1
fi
echo ""

# 测试 3: 数据清洗 (dry-run)
print_test "3. 数据清洗端点 (dry-run 模式)"
response=$(curl -s -X POST "${SERVICE_URL}/api/v1/clean" \
    -H "Content-Type: application/json" \
    -d '{"dry_run": true}')

if echo "$response" | jq -e '.success == true' > /dev/null 2>&1; then
    total_rows=$(echo "$response" | jq -r '.total_rows')
    success_rows=$(echo "$response" | jq -r '.success_rows')
    print_success "数据清洗测试通过 (总行数: ${total_rows}, 成功: ${success_rows})"
    echo "$response" | jq '{success, total_rows, success_rows, warning_rows, error_rows}'
else
    print_error "数据清洗测试失败"
    echo "$response" | jq .
    exit 1
fi
echo ""

# 测试 4: 统计信息
print_test "4. 统计信息端点"
response=$(curl -s "${SERVICE_URL}/api/v1/stats")
if echo "$response" | jq -e '.success == true' > /dev/null 2>&1; then
    total_records=$(echo "$response" | jq -r '.stats.total_records')
    unique_preachers=$(echo "$response" | jq -r '.stats.unique_preachers')
    print_success "统计信息获取成功 (记录数: ${total_records}, 讲员: ${unique_preachers})"
    echo "$response" | jq '.stats'
else
    print_error "统计信息获取失败"
    echo "$response"
    exit 1
fi
echo ""

# 测试 5: 预览数据
print_test "5. 预览数据端点"
response=$(curl -s "${SERVICE_URL}/api/v1/preview")
if echo "$response" | jq -e '.success == true' > /dev/null 2>&1; then
    count=$(echo "$response" | jq -r '.count')
    print_success "预览数据获取成功 (${count} 条记录)"
    echo "$response" | jq '{success, count, sample: .data[0]}'
else
    print_error "预览数据获取失败"
    echo "$response"
    exit 1
fi
echo ""

# 测试 6: 数据查询
print_test "6. 数据查询端点 (带过滤条件)"
response=$(curl -s -X POST "${SERVICE_URL}/api/v1/query" \
    -H "Content-Type: application/json" \
    -d '{"limit": 5}')

if echo "$response" | jq -e '.success == true' > /dev/null 2>&1; then
    count=$(echo "$response" | jq -r '.count')
    print_success "数据查询成功 (${count} 条记录)"
    echo "$response" | jq '{success, count}'
else
    print_error "数据查询失败"
    echo "$response"
    exit 1
fi
echo ""

# 所有测试通过
echo "======================================"
echo -e "${GREEN}所有测试通过！✓${NC}"
echo "======================================"
echo ""
echo "服务状态: 正常运行"
echo "API 文档: ${SERVICE_URL}/docs"
echo ""

