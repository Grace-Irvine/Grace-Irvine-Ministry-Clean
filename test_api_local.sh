#!/bin/bash
# 本地测试 FastAPI 应用
# 在部署到 Cloud Run 之前，可以用此脚本在本地测试 API

set -e

echo "============================================================"
echo "本地测试 FastAPI 应用"
echo "============================================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到 python3"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
pip3 list | grep -q fastapi || {
    echo "警告：未找到 fastapi，正在安装依赖..."
    pip3 install -r requirements.txt
}

echo "✅ 依赖检查完成"
echo ""

# 设置环境变量
export PORT=8080
export CONFIG_PATH="config/config.json"
export GOOGLE_APPLICATION_CREDENTIALS="config/service-account.json"
export SCHEDULER_TOKEN="test-token-local-only"

echo "启动 FastAPI 应用..."
echo "URL: http://localhost:8080"
echo "API 文档: http://localhost:8080/docs"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

# 启动应用
python3 app.py

