# LaMa演示系统Dockerfile

# 使用Python官方镜像作为基础
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TORCH_HOME=/app/models \
    PYTHONPATH=/app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制LaMa项目
COPY lama /app/lama

# 复制演示系统
COPY . /app

# 设置权限
RUN chmod +x /app/start.sh /app/stop.sh

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    flask==2.3.2 \
    flask-cors==4.0.0 \
    opencv-python==4.8.0.74 \
    pillow==10.0.0 \
    numpy==1.24.3 \
    pyyaml==6.0 \
    tqdm==4.66.1

# 安装PyTorch（CPU版本）
RUN pip install --no-cache-dir \
    torch==1.13.1 \
    torchvision==0.14.1 \
    --index-url https://download.pytorch.org/whl/cpu

# 创建必要的目录
RUN mkdir -p \
    /app/models \
    /tmp/lama_uploads \
    /tmp/lama_results \
    /app/logs

# 下载LaMa模型（可选）
# 注意：模型文件较大，可以在运行时挂载或下载
# RUN cd /app/lama && \
#     curl -LJO https://huggingface.co/smartywu/big-lama/resolve/main/big-lama.zip && \
#     unzip big-lama.zip && \
#     rm big-lama.zip

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/status || exit 1

# 启动命令
CMD ["python", "app.py"]

# 构建命令:
# docker build -t lama-demo .
#
# 运行命令:
# docker run -d \
#   -p 5000:5000 \
#   -v /path/to/models:/app/models \
#   -v /path/to/uploads:/tmp/lama_uploads \
#   -v /path/to/results:/tmp/lama_results \
#   --name lama-demo \
#   lama-demo