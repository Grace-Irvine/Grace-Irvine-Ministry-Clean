#!/bin/bash

# 验证并运行清洗管线

set -e

# 设置环境变量
export GOOGLE_APPLICATION_CREDENTIALS="/Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean/config/service-account.json"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   验证并运行清洗管线                                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 步骤 1: 验证权限
echo "📋 步骤 1: 验证 Google Sheets 权限"
echo "────────────────────────────────────────────────────────────"
python3 scripts/diagnose_sheets.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 权限验证失败"
    echo ""
    echo "请按照上面的提示添加服务账号权限："
    echo "  邮箱: ai-sermon-workflow-dev@ai-for-god.iam.gserviceaccount.com"
    echo "  目标表权限: 编辑者（Editor）"
    echo ""
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════"
read -p "权限验证完成。按 Enter 继续运行干跑测试..." 

# 步骤 2: 干跑测试
echo ""
echo "📋 步骤 2: 干跑模式测试"
echo "────────────────────────────────────────────────────────────"
python3 scripts/clean_pipeline.py --config config/config.json --dry-run

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 干跑测试失败"
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ 干跑测试完成！"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📊 生成的文件："
ls -lh logs/clean_preview.csv logs/clean_preview.json 2>/dev/null || echo "  (文件生成中...)"
echo ""
echo "📝 查看结果："
echo "  CSV: open logs/clean_preview.csv"
echo "  报告: cat logs/validation_report_*.txt"
echo ""
read -p "按 Enter 查看 CSV 预览的前 20 行..." 
echo ""
echo "─── CSV 预览（前 20 行）───"
head -20 logs/clean_preview.csv
echo ""
echo "════════════════════════════════════════════════════════════"
read -p "满意结果？按 Enter 运行正式清洗（或 Ctrl+C 取消）..." 

# 步骤 3: 正式运行
echo ""
echo "📋 步骤 3: 正式运行（写入目标表）"
echo "────────────────────────────────────────────────────────────"
python3 scripts/clean_pipeline.py --config config/config.json

if [ $? -eq 0 ]; then
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "🎉 清洗管线执行成功！"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "✅ 数据已写入目标表"
    echo "🔗 查看结果: https://docs.google.com/spreadsheets/d/1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc"
    echo ""
else
    echo ""
    echo "❌ 清洗管线执行失败"
    exit 1
fi

