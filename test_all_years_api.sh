#!/bin/bash
# 测试服务层 API - 生成所有年份
# 使用方法: ./test_all_years_api.sh

set -e

API_BASE="http://localhost:8080"

echo "=========================================="
echo "测试服务层 API - 所有年份生成"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 生成所有年份的服务层数据并上传到 bucket
echo -e "${BLUE}1. 生成所有年份的服务层数据（含上传）${NC}"
echo "POST $API_BASE/api/v1/service-layer/generate"
echo ""

curl -X POST "$API_BASE/api/v1/service-layer/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": ["sermon", "volunteer"],
    "generate_all_years": true,
    "upload_to_bucket": true
  }' | python3 -m json.tool

echo ""
echo ""

# 2. 仅生成 latest（不生成所有年份）
echo -e "${BLUE}2. 只生成 latest（不生成所有年份）${NC}"
echo "POST $API_BASE/api/v1/service-layer/generate"
echo ""

curl -X POST "$API_BASE/api/v1/service-layer/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": ["sermon", "volunteer"],
    "generate_all_years": false,
    "upload_to_bucket": false
  }' | python3 -m json.tool

echo ""
echo ""

# 3. 查询不同年份的数据
echo -e "${BLUE}3. 查询 2025 年证道数据（前 3 条）${NC}"
echo "GET $API_BASE/api/v1/sermon?year=2025&limit=3"
echo ""

curl -X GET "$API_BASE/api/v1/sermon?year=2025&limit=3" \
  -H "Accept: application/json" | python3 -m json.tool

echo ""
echo ""

echo -e "${GREEN}✅ 所有测试完成${NC}"
echo ""
echo "生成的文件结构:"
echo "  logs/service_layer/"
echo "  ├── sermon.json (latest)"
echo "  ├── volunteer.json (latest)"
echo "  ├── 2024/"
echo "  │   ├── sermon_2024.json"
echo "  │   └── volunteer_2024.json"
echo "  ├── 2025/"
echo "  │   ├── sermon_2025.json"
echo "  │   └── volunteer_2025.json"
echo "  └── 2026/"
echo "      ├── sermon_2026.json"
echo "      └── volunteer_2026.json"
echo ""
echo "Bucket 文件:"
echo "  gs://grace-irvine-ministry-data/domains/"
echo "  ├── sermon/"
echo "  │   ├── latest.json"
echo "  │   ├── 2024/sermon_2024.json"
echo "  │   ├── 2025/sermon_2025.json"
echo "  │   └── 2026/sermon_2026.json"
echo "  └── volunteer/"
echo "      ├── latest.json"
echo "      ├── 2024/volunteer_2024.json"
echo "      ├── 2025/volunteer_2025.json"
echo "      └── 2026/volunteer_2026.json"
echo ""

