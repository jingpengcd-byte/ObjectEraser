#!/bin/bash
# LaMa macOS 一键启动脚本 (run_mac.sh)

set -e # 遇到错误即退出

# 1. 路径准备
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
DEMO_DIR="$PROJECT_ROOT/demo"
LAMA_DIR="$PROJECT_ROOT/lama"

echo "================================================="
echo "   LaMa 图像修复系统 - macOS 一键启动脚本"
echo "================================================="

# 2. 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 python3，请先通过 Homebrew 安装 (brew install python3)"
    exit 1
fi

echo "[信息] Python 检查通过: $(python3 --version)"

# 3. 创建并激活虚拟环境
VENV_DIR="$PROJECT_ROOT/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[信息] 正在创建 Python 虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

echo "[信息] 激活虚拟环境..."
source "$VENV_DIR/bin/activate"

# 4. 安装依赖
echo "[信息] 正在更新 pip..."
pip install --upgrade pip

# macOS 推荐的 PyTorch 安装方式
echo "[信息] 正在安装 PyTorch (通过 Demo 依赖安装)..."
pip install -r "$DEMO_DIR/requirements.txt"

# 安装算法库和 Web 应用的依赖
echo "[信息] 正在安装 Lama 核心与 Demo 依赖..."
# (过滤掉 lama requirement 中的严格版本限制与容易冲突的包，例如 tensorflow, torch 等)
cat "$LAMA_DIR/requirements.txt" | cut -d'=' -f1 | grep -vE "^(tensorflow|torch|torchaudio|torchvision|scikit-learn|scikit-image)$" | xargs pip install

# 针对一些必要的且存在特定版本要求的依赖单独安装
pip install easydict omegaconf "kornia==0.5.0" "pytorch-lightning==1.2.9" scikit-image scikit-learn "numpy<2" "albumentations==0.5.2" "urllib3<2.0"



# 5. 下载预训练模型（如果缺失）
MODEL_DIR="$LAMA_DIR/big-lama"
if [ ! -d "$MODEL_DIR" ]; then
    echo "[信息] 未检测到预训练模型，正在下载 big-lama 模型..."
    # 使用 curl 下载预训练模型
    curl -L "https://huggingface.co/smartywu/big-lama/resolve/main/big-lama.zip" -o big-lama.zip
    unzip big-lama.zip -d "$LAMA_DIR"
    rm big-lama.zip
    echo "[信息] 模型下载解压完成"
else
    echo "[信息] 检测到预训练模型已存在"
fi

# 6. 启动 Web 服务
echo "[信息] 正在启动 LaMa Web Demo..."
cd "$DEMO_DIR"
# 自动通过默认浏览器打开 (后台稍后执行)
(sleep 3 && open http://127.0.0.1:5001) &
python app.py