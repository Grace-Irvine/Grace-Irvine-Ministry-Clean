#!/bin/bash
# 加载敏感信息配置文件
# 使用方法: source load-secrets.sh

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 配置文件路径
SECRETS_FILE="$SCRIPT_DIR/secrets.env"

# 检查文件是否存在
if [ ! -f "$SECRETS_FILE" ]; then
    echo "错误: 配置文件 $SECRETS_FILE 不存在" >&2
    echo "请复制 secrets.env.example 为 secrets.env 并填入实际值" >&2
    return 1 2>/dev/null || exit 1
fi

# 加载配置文件
echo "加载配置文件: $SECRETS_FILE"
source "$SECRETS_FILE"

# 验证必需变量
REQUIRED_VARS=(
    "SMTP_PASSWORD"
    "EMAIL_TO"
    "SCHEDULER_TOKEN"
    "MCP_SERVER_URL"
    "MCP_BEARER_TOKEN"
    "SMTP_USER"
    "EMAIL_FROM"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "错误: 以下必需变量未设置:" >&2
    printf '  %s\n' "${MISSING_VARS[@]}" >&2
    echo "" >&2
    echo "请在 $SECRETS_FILE 中设置这些变量" >&2
    return 1 2>/dev/null || exit 1
fi

# 设置默认值（如果配置文件中未设置）
DEFAULT_MCP_SERVER_URL="https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app"
DEFAULT_MCP_BEARER_TOKEN="eb62345c492b2bd0848d7ee4f206be82604f66f938e3e87302e0329d2baf95ff"
DEFAULT_EMAIL_FROM="jonathanjing@graceirvine.org"
DEFAULT_SMTP_USER="jonathanjing@graceirvine.org"

# 导出配置变量（从配置文件读取，如果没有则使用默认值）
export MCP_SERVER_URL=${MCP_SERVER_URL:-$DEFAULT_MCP_SERVER_URL}
export MCP_BEARER_TOKEN=${MCP_BEARER_TOKEN:-$DEFAULT_MCP_BEARER_TOKEN}
export EMAIL_FROM=${EMAIL_FROM:-$DEFAULT_EMAIL_FROM}
export SMTP_USER=${SMTP_USER:-$DEFAULT_SMTP_USER}
export SMTP_SERVER=${SMTP_SERVER:-"smtp.gmail.com"}
export SMTP_PORT=${SMTP_PORT:-"587"}

echo "✓ 配置加载成功"
echo "  SMTP User: $SMTP_USER"
echo "  Email From: $EMAIL_FROM"
echo "  Email To: $EMAIL_TO"
echo "  Email CC: ${EMAIL_CC:-未设置}"
echo "  MCP Server: $MCP_SERVER_URL"
