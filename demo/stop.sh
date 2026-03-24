#!/bin/bash
# LaMa演示系统停止脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
DEMO_DIR="/home/guojingpeng/workSpace/demo"
PID_FILE="$DEMO_DIR/demo.pid"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 停止演示系统
stop_demo() {
    print_info "正在停止LaMa演示系统..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        
        # 检查进程是否存在
        if ps -p $PID > /dev/null 2>&1; then
            print_info "找到运行进程 (PID: $PID)"
            
            # 尝试正常停止
            print_info "发送停止信号..."
            kill $PID
            
            # 等待进程停止
            for i in {1..10}; do
                if ! ps -p $PID > /dev/null 2>&1; then
                    print_success "演示系统已正常停止"
                    rm -f "$PID_FILE"
                    return 0
                fi
                sleep 1
            done
            
            # 如果正常停止失败，强制停止
            print_warning "正常停止失败，尝试强制停止..."
            kill -9 $PID
            
            sleep 2
            
            if ! ps -p $PID > /dev/null 2>&1; then
                print_success "演示系统已强制停止"
                rm -f "$PID_FILE"
            else
                print_error "无法停止进程，请手动检查"
                return 1
            fi
            
        else
            print_warning "PID文件存在但进程不存在，清理残留文件"
            rm -f "$PID_FILE"
        fi
        
    else
        print_warning "未找到PID文件，演示系统可能未运行"
        
        # 尝试查找并停止相关进程
        print_info "查找相关Python进程..."
        PIDS=$(ps aux | grep "python3.*app.py" | grep -v grep | awk '{print $2}')
        
        if [ -n "$PIDS" ]; then
            print_info "找到相关进程: $PIDS"
            for PID in $PIDS; do
                print_info "停止进程: $PID"
                kill $PID
            done
            sleep 2
            print_success "相关进程已停止"
        else
            print_info "未找到相关Python进程"
        fi
    fi
    
    return 0
}

# 清理临时文件
cleanup_temp_files() {
    print_info "清理临时文件..."
    
    # 清理上传和结果目录
    TEMP_DIRS=(
        "/tmp/lama_uploads"
        "/tmp/lama_results"
        "$DEMO_DIR/logs"
    )
    
    for dir in "${TEMP_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            print_info "清理目录: $dir"
            rm -rf "$dir"/*
        fi
    done
    
    # 清理日志文件
    if [ -f "$DEMO_DIR/demo.log" ]; then
        print_info "清理日志文件"
        > "$DEMO_DIR/demo.log"
    fi
    
    print_success "临时文件清理完成"
}

# 显示状态
show_status() {
    print_info "当前服务状态:"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            PORT=$(lsof -Pan -p $PID -i 2>/dev/null | grep LISTEN | awk '{print $9}' | cut -d: -f2 | head -1)
            echo -e "  • 运行状态: ${GREEN}运行中${NC}"
            echo "  • 进程ID: $PID"
            echo "  • 端口号: $PORT"
        else
            echo -e "  • 运行状态: ${RED}已停止（残留PID文件）${NC}"
        fi
    else
        echo -e "  • 运行状态: ${YELLOW}已停止${NC}"
    fi
    
    # 检查是否有其他相关进程
    OTHER_PIDS=$(ps aux | grep "python3.*app.py" | grep -v grep | awk '{print $2}' | tr '\n' ' ')
    if [ -n "$OTHER_PIDS" ]; then
        echo -e "  • 其他相关进程: ${YELLOW}$OTHER_PIDS${NC}"
    fi
}

# 显示帮助
show_help() {
    cat << EOF
LaMa演示系统停止脚本

用法: $0 [选项]

选项:
  stop        停止演示系统（默认）
  clean       停止并清理临时文件
  status      查看服务状态
  --help     显示此帮助信息

示例:
  $0            # 停止演示系统
  $0 stop      # 停止演示系统
  $0 clean     # 停止并清理临时文件
  $0 status    # 查看服务状态
EOF
}

# 主函数
main() {
    ACTION="stop"  # 默认动作
    
    # 解析参数
    while [ $# -gt 0 ]; do
        case $1 in
            stop|clean|status)
                ACTION=$1
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
        shift
    done
    
    # 执行动作
    case $ACTION in
        stop)
            stop_demo
            ;;
        clean)
            stop_demo
            cleanup_temp_files
            ;;
        status)
            show_status
            ;;
    esac
    
    exit 0
}

# 运行主函数
main "$@"