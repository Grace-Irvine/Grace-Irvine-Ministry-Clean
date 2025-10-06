#!/bin/bash

# 测试运行脚本
# 用于快速测试清洗管线

set -e

echo "=========================================="
echo "🧪 测试清洗管线"
echo "=========================================="
echo ""

# 检查服务账号凭证
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "⚠️  警告: GOOGLE_APPLICATION_CREDENTIALS 环境变量未设置"
    echo ""
    echo "请运行以下命令之一："
    echo ""
    echo "1. 如果服务账号 JSON 文件在当前目录："
    echo "   export GOOGLE_APPLICATION_CREDENTIALS=\"\$(pwd)/你的服务账号文件.json\""
    echo ""
    echo "2. 或指定完整路径："
    echo "   export GOOGLE_APPLICATION_CREDENTIALS=\"/完整路径/你的服务账号文件.json\""
    echo ""
    echo "3. 然后重新运行此脚本："
    echo "   ./run_test.sh"
    echo ""
    exit 1
fi

echo "✅ 服务账号凭证: $GOOGLE_APPLICATION_CREDENTIALS"
echo ""

# 检查文件是否存在
if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "❌ 错误: 服务账号文件不存在: $GOOGLE_APPLICATION_CREDENTIALS"
    exit 1
fi

# 步骤 1: 干跑模式测试
echo "📋 步骤 1: 干跑模式测试（不写回 Google Sheet）"
echo "----------------------------------------"
python3 scripts/clean_pipeline.py --config config/config.json --dry-run

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 干跑测试失败，请检查错误信息"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 干跑测试完成！"
echo "=========================================="
echo ""
echo "📊 生成的文件："
echo "  - logs/clean_preview.csv"
echo "  - logs/clean_preview.json"
echo "  - logs/validation_report_*.txt"
echo ""
echo "📝 下一步："
echo "  1. 检查 logs/clean_preview.csv，确认清洗结果正确"
echo "  2. 如果满意，运行正式清洗："
echo "     python3 scripts/clean_pipeline.py --config config/config.json"
echo ""
echo "  或使用便捷脚本："
echo "     ./run_pipeline.sh"
echo ""

