#!/bin/bash
# 测试服务层 API 端点
# 使用方法: ./test_service_layer.sh

set -e

API_BASE="http://localhost:8080"

echo "=========================================="
echo "测试服务层 API 端点"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 测试生成服务层数据
echo -e "${BLUE}1. 生成服务层数据${NC}"
echo "POST $API_BASE/api/v1/service-layer/generate"
echo ""

curl -X POST "$API_BASE/api/v1/service-layer/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": ["sermon", "volunteer"],
    "force": false,
    "upload_to_bucket": false
  }' | python3 -m json.tool

echo ""
echo ""

# 2. 测试获取证道域数据
echo -e "${BLUE}2. 获取证道域数据 (2024年, 前5条)${NC}"
echo "GET $API_BASE/api/v1/sermon?year=2024&limit=5"
echo ""

curl -X GET "$API_BASE/api/v1/sermon?year=2024&limit=5" \
  -H "Accept: application/json" | python3 -m json.tool

echo ""
echo ""

# 3. 测试获取同工域数据
echo -e "${BLUE}3. 获取同工域数据 (2024年, 前5条)${NC}"
echo "GET $API_BASE/api/v1/volunteer?year=2024&limit=5"
echo ""

curl -X GET "$API_BASE/api/v1/volunteer?year=2024&limit=5" \
  -H "Accept: application/json" | python3 -m json.tool

echo ""
echo ""

# 4. 测试按日期查询同工数据
echo -e "${BLUE}4. 获取特定日期的同工数据${NC}"
echo "GET $API_BASE/api/v1/volunteer?service_date=2024-01-07"
echo ""

curl -X GET "$API_BASE/api/v1/volunteer?service_date=2024-01-07" \
  -H "Accept: application/json" | python3 -m json.tool

echo ""
echo ""

echo -e "${GREEN}✅ 服务层 API 测试完成${NC}"
echo ""
echo "本地生成的文件:"
echo "  - logs/service_layer/sermon.json"
echo "  - logs/service_layer/volunteer.json"
echo ""

