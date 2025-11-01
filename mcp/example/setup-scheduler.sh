#!/bin/bash
# 快速设置每周事工预览定时器服务
# 使用方法: ./setup-scheduler.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}每周事工预览定时器服务快速设置${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查敏感信息配置文件
SECRETS_FILE="secrets.env"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ ! -f "$SECRETS_FILE" ]; then
  echo -e "${YELLOW}配置文件 $SECRETS_FILE 不存在${NC}"
  echo -e "${YELLOW}从示例文件创建...${NC}"
  cp secrets.env.example "$SECRETS_FILE"
  chmod 600 "$SECRETS_FILE"  # 设置权限，仅所有者可读写
  echo -e "${GREEN}已创建配置文件: $SECRETS_FILE${NC}"
  echo ""
  echo -e "${YELLOW}请编辑 $SECRETS_FILE 并填入以下必需信息:${NC}"
  echo "  1. SMTP_PASSWORD - Gmail 应用专用密码"
  echo "  2. EMAIL_TO - 收件人邮箱地址"
  echo "  3. EMAIL_CC - 抄送邮箱地址（可选）"
  echo "  4. SCHEDULER_TOKEN - 安全的随机令牌"
  echo ""
  echo -e "${YELLOW}提示: 可以运行 'openssl rand -hex 32' 生成 SCHEDULER_TOKEN${NC}"
  echo ""
  read -p "按 Enter 继续编辑配置文件，或 Ctrl+C 退出..."
  ${EDITOR:-nano} "$SECRETS_FILE"
fi

# 设置文件权限（确保只有所有者可以访问）
chmod 600 "$SECRETS_FILE"

# 加载配置
echo -e "${GREEN}加载配置文件...${NC}"
source "$SCRIPT_DIR/load-secrets.sh"

# 验证必需变量
if [ -z "$SMTP_PASSWORD" ]; then
  echo -e "${RED}错误: SMTP_PASSWORD 未设置${NC}"
  exit 1
fi

if [ -z "$EMAIL_TO" ]; then
  echo -e "${RED}错误: EMAIL_TO 未设置${NC}"
  exit 1
fi

if [ -z "$SCHEDULER_TOKEN" ]; then
  echo -e "${RED}错误: SCHEDULER_TOKEN 未设置${NC}"
  echo -e "${YELLOW}生成随机令牌...${NC}"
  SCHEDULER_TOKEN=$(openssl rand -hex 32)
  echo "SCHEDULER_TOKEN=$SCHEDULER_TOKEN" >> "$SECRETS_FILE"
  echo -e "${GREEN}已生成并保存 SCHEDULER_TOKEN 到 $SECRETS_FILE${NC}"
fi

# 配置已经在 load-secrets.sh 中加载并导出，无需重复设置
# 所有配置值现在从 secrets.env 文件中读取

# 显示配置摘要
echo ""
echo -e "${GREEN}配置摘要:${NC}"
echo "  MCP Server: $MCP_SERVER_URL"
echo "  发件人: $EMAIL_FROM"
echo "  收件人: $EMAIL_TO"
echo "  Scheduler Token: ${SCHEDULER_TOKEN:0:20}..."
echo ""

# 确认部署
read -p "是否开始部署? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "已取消部署"
  exit 1
fi

# 运行部署脚本
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
"$SCRIPT_DIR/deploy.sh"
