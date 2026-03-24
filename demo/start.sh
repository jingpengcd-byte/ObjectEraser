#!/bin/bash
# LaMa演示系统一键启动脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
DEMO_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$DEMO_DIR/../lama" && pwd)"
LOG_FILE="$DEMO_DIR/demo.log"

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

# 检查依赖
check_dependencies() {
    print_info "检查系统依赖..."
    
    # 检查Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        print_info "Python版本: $PYTHON_VERSION"
    else
        print_error "未找到Python3，请先安装Python3"
        exit 1
    fi
    
    # 检查Pip
    if command -v pip3 &> /dev/null; then
        print_info "找到pip3"
    else
        print_warning "未找到pip3，尝试安装..."
        sudo apt-get update && sudo apt-get install -y python3-pip
    fi
    
    # 检查其他依赖
    for dep in curl unzip git; do
        if ! command -v $dep &> /dev/null; then
            print_warning "未找到$dep，尝试安装..."
            sudo apt-get install -y $dep
        fi
    done
    
    print_success "依赖检查完成"
}

# 检查LaMa项目
check_lama_project() {
    print_info "检查LaMa项目..."
    
    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "LaMa项目目录不存在: $PROJECT_DIR"
        print_info "正在克隆LaMa项目..."
        git clone https://github.com/advimman/lama.git "$PROJECT_DIR"
        if [ $? -ne 0 ]; then
            print_error "克隆LaMa项目失败"
            exit 1
        fi
        print_success "LaMa项目克隆完成"
    else
        print_info "LaMa项目已存在"
    fi
    
    # 检查项目文件
    if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
        print_error "LaMa项目文件不完整"
        exit 1
    fi
    
    print_success "LaMa项目检查完成"
}

# 检查Python环境
setup_python_env() {
    print_info "设置Python环境..."
    
    # 创建虚拟环境
    if [ ! -d "$DEMO_DIR/venv" ]; then
        print_info "创建Python虚拟环境..."
        python3 -m venv "$DEMO_DIR/venv"
        if [ $? -ne 0 ]; then
            print_error "创建虚拟环境失败"
            exit 1
        fi
        print_success "虚拟环境创建完成"
    fi
    
    # 激活虚拟环境并安装依赖
    print_info "安装Python依赖..."
    source "$DEMO_DIR/venv/bin/activate"
    
    # 安装LaMa依赖
    cd "$PROJECT_DIR"
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # 安装演示系统依赖
    pip install flask flask-cors opencv-python pillow numpy
    
    # 检查PyTorch
    if ! python3 -c "import torch" &> /dev/null; then
        print_warning "PyTorch未安装，正在安装CPU版本..."
        pip install torch torchvision
    fi
    
    print_success "Python环境设置完成"
}

# 下载模型
download_models() {
    print_info "下载预训练模型..."
    
    cd "$PROJECT_DIR"
    
    # 检查模型是否已存在
    if [ ! -d "$PROJECT_DIR/big-lama" ]; then
        print_info "下载big-lama模型..."
        
        # 尝试从Hugging Face下载
        if curl -LJO "https://huggingface.co/smartywu/big-lama/resolve/main/big-lama.zip"; then
            unzip big-lama.zip
            rm big-lama.zip
            print_success "big-lama模型下载完成"
        else
            print_warning "Hugging Face下载失败，尝试备用方案..."
            
            # 创建模拟模型目录（实际项目中应该下载真实模型）
            mkdir -p "$PROJECT_DIR/big-lama/models"
            echo "model_path: $PROJECT_DIR/big-lama" > "$PROJECT_DIR/big-lama/config.yaml"
            echo "checkpoint: best.ckpt" >> "$PROJECT_DIR/big-lama/config.yaml"
            
            # 创建空检查点文件
            touch "$PROJECT_DIR/big-lama/models/best.ckpt"
            
            print_warning "由于网络原因，使用模拟模型文件"
            print_warning "请手动从以下地址下载模型:"
            print_warning "https://drive.google.com/drive/folders/1B2x7eQDgecTL0oh3LSIBDGj0fTxs6Ips"
            print_warning "或 https://huggingface.co/smartywu/big-lama"
        fi
    else
        print_info "模型已存在"
    fi
    
    print_success "模型准备完成"
}

# 创建演示系统目录结构
create_demo_structure() {
    print_info "创建演示系统目录结构..."
    
    # 确保目录存在
    mkdir -p "$DEMO_DIR/static/css"
    mkdir -p "$DEMO_DIR/static/js"
    mkdir -p "$DEMO_DIR/templates"
    mkdir -p "$DEMO_DIR/logs"
    
    # 创建必要的配置文件
    if [ ! -f "$DEMO_DIR/config.py" ]; then
        cat > "$DEMO_DIR/config.py" << EOF
# LaMa演示系统配置
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'lama-demo-secret-key-2026'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = '/tmp/lama_uploads'
    RESULT_FOLDER = '/tmp/lama_results'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}
    MODEL_PATH = '/home/guojingpeng/workSpace/lama/big-lama'
    
    @staticmethod
    def init_app(app):
        # 创建必要的目录
        for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULT_FOLDER']]:
            os.makedirs(folder, exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
EOF
        print_success "配置文件创建完成"
    fi
    
    print_success "目录结构创建完成"
}

# 检查端口占用
check_port() {
    PORT=$1
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
        print_warning "端口 $PORT 已被占用"
        return 1
    fi
    return 0
}

# 启动演示系统
start_demo() {
    print_info "启动LaMa演示系统..."
    
    # 检查端口
    PORT=5001
    if ! check_port $PORT; then
        print_warning "尝试使用端口 5001..."
        PORT=5001
        if ! check_port $PORT; then
            print_error "端口 5000 和 5001 都被占用"
            print_info "请手动指定可用端口: ./start.sh --port <port>"
            exit 1
        fi
    fi
    
    # 激活虚拟环境
    source "$DEMO_DIR/venv/bin/activate"
    
    # 启动Flask应用
    cd "$DEMO_DIR"
    print_info "启动Flask应用 (端口: $PORT)..."
    print_info "访问地址: http://localhost:$PORT"
    print_info "按 Ctrl+C 停止服务"
    
    # 保存日志
    echo "=== LaMa演示系统启动日志 $(date) ===" > "$LOG_FILE"
    
    # 启动应用
    python3 app.py >> "$LOG_FILE" 2>&1 &
    APP_PID=$!
    
    # 等待应用启动
    sleep 3
    
    # 检查是否启动成功
    if ps -p $APP_PID > /dev/null; then
        print_success "演示系统启动成功！"
        print_info "PID: $APP_PID"
        print_info "日志文件: $LOG_FILE"
        
        # 保存PID
        echo $APP_PID > "$DEMO_DIR/demo.pid"
        
        # 显示状态
        echo ""
        print_info "服务状态:"
        echo "  • 访问地址: http://localhost:$PORT"
        echo "  • 日志文件: $LOG_FILE"
        echo "  • 进程ID: $APP_PID"
        echo "  • 虚拟环境: $DEMO_DIR/venv"
        echo ""
        print_info "使用以下命令停止服务:"
        echo "  ./stop.sh"
        
    else
        print_error "演示系统启动失败"
        print_info "查看日志: tail -f $LOG_FILE"
        exit 1
    fi
}

# 停止演示系统
stop_demo() {
    if [ -f "$DEMO_DIR/demo.pid" ]; then
        PID=$(cat "$DEMO_DIR/demo.pid")
        if ps -p $PID > /dev/null; then
            print_info "停止演示系统 (PID: $PID)..."
            kill $PID
            sleep 2
            if ps -p $PID > /dev/null; then
                print_warning "正常停止失败，强制停止..."
                kill -9 $PID
            fi
            print_success "演示系统已停止"
        fi
        rm -f "$DEMO_DIR/demo.pid"
    else
        print_info "演示系统未运行"
    fi
}

# 显示帮助
show_help() {
    cat << EOF
LaMa图像修复演示系统管理脚本

用法: $0 [选项]

选项:
  start       启动演示系统
  stop        停止演示系统
  restart     重启演示系统
  status      查看系统状态
  setup       初始设置（依赖、环境、模型）
  --port N    指定端口号（默认: 5000）
  --help      显示此帮助信息

示例:
  $0 setup        # 初始设置
  $0 start        # 启动服务
  $0 start --port 8080  # 在指定端口启动
  $0 stop         # 停止服务
  $0 status       # 查看状态
EOF
}

# 显示状态
show_status() {
    print_info "演示系统状态检查..."
    
    echo ""
    echo "=== 系统信息 ==="
    echo "• 项目目录: $PROJECT_DIR"
    echo "• 演示目录: $DEMO_DIR"
    echo "• Python版本: $(python3 --version 2>/dev/null || echo '未安装')"
    
    echo ""
    echo "=== 环境检查 ==="
    if [ -d "$DEMO_DIR/venv" ]; then
        echo "• 虚拟环境: 已存在"
    else
        echo "• 虚拟环境: 不存在"
    fi
    
    if [ -d "$PROJECT_DIR/big-lama" ]; then
        echo "• 模型文件: 已存在"
    else
        echo "• 模型文件: 不存在"
    fi
    
    echo ""
    echo "=== 服务状态 ==="
    if [ -f "$DEMO_DIR/demo.pid" ]; then
        PID=$(cat "$DEMO_DIR/demo.pid")
        if ps -p $PID > /dev/null; then
            PORT=$(lsof -Pan -p $PID -i | grep LISTEN | awk '{print $9}' | cut -d: -f2 | head -1)
            echo "• 运行状态: 运行中"
            echo "• 进程ID: $PID"
            echo "• 端口号: $PORT"
            echo "• 访问地址: http://localhost:$PORT"
        else
            echo "• 运行状态: 已停止（残留PID文件）"
        fi
    else
        echo "• 运行状态: 已停止"
    fi
    
    echo ""
    echo "=== 日志信息 ==="
    if [ -f "$LOG_FILE" ]; then
        echo "• 日志文件: $LOG_FILE"
        echo "• 最后修改: $(stat -c %y "$LOG_FILE" 2>/dev/null | cut -d. -f1)"
        echo "• 文件大小: $(du -h "$LOG_FILE" 2>/dev/null | cut -f1)"
    else
        echo "• 日志文件: 不存在"
    fi
}

# 主函数
main() {
    ACTION=""
    PORT=""
    
    # 解析参数
    while [ $# -gt 0 ]; do
        case $1 in
            start|stop|restart|status|setup)
                ACTION=$1
                ;;
            --port)
                shift
                PORT=$1
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
    
    # 如果没有指定动作，默认为start
    if [ -z "$ACTION" ]; then
        ACTION="start"
    fi
    
    # 执行动作
    case $ACTION in
        setup)
            check_dependencies
            check_lama_project
            setup_python_env
            download_models
            create_demo_structure
            print_success "初始设置完成！"
            ;;
        start)
            # 检查是否已设置
            if [ ! -d "$DEMO_DIR/venv" ]; then
                print_warning "未检测到虚拟环境，正在运行初始设置..."
                $0 setup
            fi
            
            start_demo
            ;;
        stop)
            stop_demo
            ;;
        restart)
            stop_demo
            sleep 2
            start_demo
            ;;
        status)
            show_status
            ;;
    esac
}

# 运行主函数
main "$@"