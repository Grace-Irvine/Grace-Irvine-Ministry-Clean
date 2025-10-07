#!/bin/bash
# 测试变化检测功能

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_URL="${SERVICE_URL:-https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app}"

print_test() {
    echo -e "${YELLOW}[测试]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo "======================================"
echo "  测试变化检测功能"
echo "======================================"
echo ""

# 测试 1: 首次强制执行（建立基线）
print_test "1. 首次执行（强制模式）- 建立数据基线"
response=$(curl -s -X POST "${SERVICE_URL}/api/v1/clean" \
    -H "Content-Type: application/json" \
    -d '{"dry_run": true, "force": true}')

success=$(echo "$response" | jq -r '.success')
changed=$(echo "$response" | jq -r '.changed')
change_reason=$(echo "$response" | jq -r '.change_reason')

if [ "$success" = "true" ] && [ "$changed" = "true" ]; then
    print_success "首次执行成功"
    print_info "变化原因: $change_reason"
    echo "$response" | jq '{success, changed, change_reason, total_rows, success_rows}'
else
    echo "❌ 测试失败"
    echo "$response" | jq .
    exit 1
fi
echo ""

# 等待一下
sleep 2

# 测试 2: 立即再次执行（应该检测到无变化）
print_test "2. 立即再次执行 - 应检测到无变化"
response=$(curl -s -X POST "${SERVICE_URL}/api/v1/clean" \
    -H "Content-Type: application/json" \
    -d '{"dry_run": true}')

success=$(echo "$response" | jq -r '.success')
changed=$(echo "$response" | jq -r '.changed')
change_reason=$(echo "$response" | jq -r '.change_reason')
message=$(echo "$response" | jq -r '.message')

if [ "$success" = "true" ] && [ "$changed" = "false" ]; then
    print_success "变化检测正常 - 成功识别无变化"
    print_info "原因: $change_reason"
    print_info "消息: $message"
    echo "$response" | jq '{success, changed, change_reason, message, last_update_time}'
else
    echo "❌ 测试失败 - 应该检测到无变化"
    echo "$response" | jq .
    exit 1
fi
echo ""

# 测试 3: 再次强制执行
print_test "3. 强制执行 - 跳过变化检测"
response=$(curl -s -X POST "${SERVICE_URL}/api/v1/clean" \
    -H "Content-Type: application/json" \
    -d '{"dry_run": true, "force": true}')

success=$(echo "$response" | jq -r '.success')
changed=$(echo "$response" | jq -r '.changed')
change_reason=$(echo "$response" | jq -r '.change_reason')

if [ "$success" = "true" ] && [ "$changed" = "true" ] && [ "$change_reason" = "forced" ]; then
    print_success "强制执行成功"
    echo "$response" | jq '{success, changed, change_reason}'
else
    echo "❌ 测试失败"
    echo "$response" | jq .
    exit 1
fi
echo ""

# 测试 4: 测试定时任务端点
print_test "4. 测试定时任务触发端点"
print_info "使用认证令牌调用 /trigger-cleaning"

if [ -z "$SCHEDULER_TOKEN" ]; then
    SCHEDULER_TOKEN="2aabb0d776fe8961a6c40e507a2ecd548a1e46947438328350a1494318b229dd"
    print_info "使用默认 SCHEDULER_TOKEN"
fi

response=$(curl -s -X POST "${SERVICE_URL}/trigger-cleaning" \
    -H "Authorization: Bearer ${SCHEDULER_TOKEN}" \
    -H "Content-Type: application/json")

success=$(echo "$response" | jq -r '.success')
if [ "$success" = "true" ]; then
    print_success "定时任务端点调用成功"
    changed=$(echo "$response" | jq -r '.changed')
    if [ "$changed" = "false" ]; then
        print_info "数据未变化，跳过了更新（符合预期）"
    else
        print_info "数据有变化，执行了更新"
    fi
    echo "$response" | jq '{success, changed, change_reason, message}'
else
    echo "❌ 测试失败"
    echo "$response" | jq .
    exit 1
fi
echo ""

# 所有测试通过
echo "======================================"
echo -e "${GREEN}所有测试通过！✓${NC}"
echo "======================================"
echo ""
echo "变化检测功能总结："
echo "  ✓ 首次运行正常（建立基线）"
echo "  ✓ 无变化时跳过更新（节省资源）"
echo "  ✓ 强制执行模式正常"
echo "  ✓ 定时任务端点正常"
echo ""
echo "定时任务配置："
echo "  执行频率: 每30分钟"
echo "  下次执行: $(gcloud scheduler jobs describe ministry-data-cleaning-scheduler --location=us-central1 --format='value(scheduleTime)' 2>/dev/null || echo '请运行 setup-cloud-scheduler.sh')"
echo ""

