#!/bin/bash
# MCP 包构建脚本

set -e

echo "🚀 开始构建 MCP 包..."

# 检查必要文件是否存在
echo "📋 检查必要文件..."

required_files=(
    "config/config.json"
    "config/service-account.json"
    "mcp_local/mcp_server.py"
    "mcp_local/sse_transport.py"
    "core/clean_pipeline.py"
    "core/service_layer.py"
    "core/cloud_storage_utils.py"
    "core/gsheet_utils.py"
    "core/alias_utils.py"
    "core/change_detector.py"
    "core/schema_manager.py"
    "core/validators.py"
    "core/debug_clean_local.py"
    "core/detect_schema_changes.py"
    "core/extract_aliases_smart.py"
    "core/generate_aliases_from_excel.py"
    "core/generate_volunteer_metadata.py"
    "requirements.txt"
    "manifest.json"
    "icon.png"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ 缺少必要文件: $file"
        exit 1
    else
        echo "✅ $file"
    fi
done

echo ""
echo "📦 所有必要文件都存在，MCP 包已准备就绪！"
echo ""
echo "📝 使用说明："
echo "1. 将整个项目目录复制到 Claude Desktop 的 MCP 扩展目录"
echo "2. 确保 config/service-account.json 包含有效的 GCS 凭据"
echo "3. 确保 config/config.json 配置正确"
echo "4. 重启 Claude Desktop 以加载 MCP 包"
echo ""
echo "🔧 环境变量配置："
echo "   GOOGLE_APPLICATION_CREDENTIALS: \${__dirname}/config/service-account.json"
echo "   CONFIG_PATH: \${__dirname}/config/config.json"
echo ""
echo "✅ 构建完成！"
