#!/bin/bash

# 教会主日事工数据清洗管线执行脚本

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境变量
check_credentials() {
    if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        print_error "未设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量"
        print_info "请运行: export GOOGLE_APPLICATION_CREDENTIALS=\"/path/to/your-service-account.json\""
        exit 1
    fi
    
    if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        print_error "凭证文件不存在: $GOOGLE_APPLICATION_CREDENTIALS"
        exit 1
    fi
    
    print_info "凭证文件: $GOOGLE_APPLICATION_CREDENTIALS"
}

# 检查配置文件
check_config() {
    CONFIG_FILE="${1:-config/config.json}"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "配置文件不存在: $CONFIG_FILE"
        exit 1
    fi
    
    print_info "配置文件: $CONFIG_FILE"
}

# 显示帮助信息
show_help() {
    cat << EOF
用法: $0 [选项]

选项:
    --dry-run           干跑模式（仅生成预览，不写回 Google Sheet）
    --config FILE       指定配置文件（默认: config/config.json）
    --test              运行单元测试
    --help              显示此帮助信息

示例:
    # 干跑模式
    $0 --dry-run
    
    # 正式运行
    $0
    
    # 使用自定义配置
    $0 --config config/custom.json
    
    # 运行测试
    $0 --test

EOF
}

# 运行测试
run_tests() {
    print_info "运行单元测试..."
    pytest tests/test_cleaning.py -v
    print_info "测试完成！"
}

# 显示欢迎信息
show_banner() {
    cat << 'EOF'
╔═══════════════════════════════════════════════════════════╗
║   教会主日事工数据清洗管线                                ║
║   Church Ministry Data Cleaning Pipeline v1.0.0          ║
╚═══════════════════════════════════════════════════════════╝
EOF
}

# 主函数
main() {
    show_banner
    echo ""
    # 解析参数
    DRY_RUN=""
    CONFIG_FILE="config/config.json"
    RUN_TEST=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN="--dry-run"
                shift
                ;;
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --test)
                RUN_TEST=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 运行测试
    if [ "$RUN_TEST" = true ]; then
        run_tests
        exit 0
    fi
    
    # 检查环境
    print_info "检查运行环境..."
    check_credentials
    check_config "$CONFIG_FILE"
    
    # 创建日志目录
    mkdir -p logs
    
    # 运行管线
    if [ -n "$DRY_RUN" ]; then
        print_warning "运行干跑模式（不会写入 Google Sheet）"
    else
        print_info "运行正式清洗管线"
    fi
    
    python scripts/clean_pipeline.py --config "$CONFIG_FILE" $DRY_RUN
    
    # 检查退出码
    if [ $? -eq 0 ]; then
        print_info "清洗管线执行成功！"
        
        if [ -n "$DRY_RUN" ]; then
            print_info "预览文件已生成:"
            [ -f "logs/clean_preview.csv" ] && echo "  - logs/clean_preview.csv"
            [ -f "logs/clean_preview.json" ] && echo "  - logs/clean_preview.json"
        fi
    else
        print_error "清洗管线执行失败，请查看日志文件"
        exit 1
    fi
}

main "$@"

