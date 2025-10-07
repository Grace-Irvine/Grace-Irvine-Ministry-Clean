#!/bin/bash
# 快速生成同工元数据的脚本

cd "$(dirname "$0")"
export GOOGLE_APPLICATION_CREDENTIALS="config/service-account.json"

echo "🚀 开始生成同工元数据..."
python3 scripts/generate_volunteer_metadata.py "$@"

