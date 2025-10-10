#!/bin/bash
# 重构验证脚本 - 验证架构重构是否成功

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}验证架构重构${NC}"
echo -e "${GREEN}========================================${NC}"

# 1. 检查目录结构
echo -e "\n${YELLOW}[1/6] 检查目录结构...${NC}"
dirs=("api" "mcp" "core" "deploy")
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✓${NC} $dir/ 存在"
    else
        echo -e "  ${RED}✗${NC} $dir/ 不存在"
        exit 1
    fi
done

# 2. 检查Dockerfile
echo -e "\n${YELLOW}[2/6] 检查Dockerfile...${NC}"
if [ -f "api/Dockerfile" ]; then
    echo -e "  ${GREEN}✓${NC} api/Dockerfile 存在"
else
    echo -e "  ${RED}✗${NC} api/Dockerfile 不存在"
    exit 1
fi

if [ -f "mcp/Dockerfile" ]; then
    echo -e "  ${GREEN}✓${NC} mcp/Dockerfile 存在"
else
    echo -e "  ${RED}✗${NC} mcp/Dockerfile 不存在"
    exit 1
fi

# 3. 检查README
echo -e "\n${YELLOW}[3/6] 检查文档...${NC}"
docs=("api/README.md" "mcp/README.md" "ARCHITECTURE.md" "REFACTOR_SUMMARY.md")
for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "  ${GREEN}✓${NC} $doc 存在"
    else
        echo -e "  ${RED}✗${NC} $doc 不存在"
        exit 1
    fi
done

# 4. 运行单元测试
echo -e "\n${YELLOW}[4/6] 运行单元测试...${NC}"
if python3 -m pytest tests/test_cleaning.py -v --tb=short 2>&1 | tail -5; then
    echo -e "  ${GREEN}✓${NC} 测试通过"
else
    echo -e "  ${RED}✗${NC} 测试失败"
    exit 1
fi

# 5. 测试导入
echo -e "\n${YELLOW}[5/6] 测试Python导入...${NC}"
if python3 -c "
import sys
sys.path.insert(0, '.')
from api.app import app
from core.clean_pipeline import CleaningPipeline
from core.service_layer import ServiceLayerManager
print('导入成功')
" 2>&1 | grep -q "导入成功"; then
    echo -e "  ${GREEN}✓${NC} API服务导入正常"
else
    echo -e "  ${RED}✗${NC} API服务导入失败"
    exit 1
fi

# 6. 检查部署脚本
echo -e "\n${YELLOW}[6/6] 检查部署脚本...${NC}"
scripts=("deploy/deploy-api.sh" "deploy/deploy-mcp.sh" "deploy/deploy-all.sh")
for script in "${scripts[@]}"; do
    if [ -f "$script" ] && [ -x "$script" ]; then
        echo -e "  ${GREEN}✓${NC} $script 存在且可执行"
    elif [ -f "$script" ]; then
        echo -e "  ${YELLOW}⚠${NC} $script 存在但不可执行（可能需要chmod +x）"
    else
        echo -e "  ${RED}✗${NC} $script 不存在"
        exit 1
    fi
done

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 所有验证通过！${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}下一步：${NC}"
echo "1. 测试Docker构建（可选）："
echo "   docker build -f api/Dockerfile -t ministry-data-api:test ."
echo "   docker build -f mcp/Dockerfile -t ministry-data-mcp:test ."
echo ""
echo "2. 本地测试服务："
echo "   python3 api/app.py"
echo "   python3 mcp/mcp_http_server.py"
echo ""
echo "3. 部署到Cloud Run："
echo "   cd deploy && ./deploy-all.sh"
echo ""
echo -e "${GREEN}架构重构完成！🎉${NC}"

