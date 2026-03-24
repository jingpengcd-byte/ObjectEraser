# LaMa图像修复演示系统

基于LaMa（Large Mask Inpainting with Fourier Convolutions）深度学习的图像修复Web应用程序。

## 项目特点

- 🎨 **交互式界面**: 直观的Web界面，支持拖拽上传和画布操作
- ⚡ **快速修复**: 集成LaMa深度学习模型，支持高质量图像修复
- 🔧 **多种工具**: 提供画笔、矩形、橡皮擦等掩码绘制工具
- 📱 **响应式设计**: 适配桌面和移动设备
- 🐳 **容器化支持**: 提供Docker部署方案

## 系统要求

### 最低配置
- CPU: 4核以上
- 内存: 8GB RAM
- 存储: 10GB可用空间
- 操作系统: Ubuntu 18.04+/CentOS 7+/macOS 10.15+

### 推荐配置（GPU加速）
- GPU: NVIDIA GPU (支持CUDA)
- 显存: 8GB以上
- CUDA版本: 10.2+

## 快速开始

### 方法一：使用一键启动脚本（推荐）

```bash
# 1. 确保LaMa项目已克隆
cd /home/guojingpeng/workSpace
git clone https://github.com/advimman/lama.git

# 2. 进入演示目录
cd demo

# 3. 初始设置（自动安装依赖和虚拟环境）
chmod +x start.sh stop.sh
./start.sh setup

# 4. 启动服务
./start.sh

# 5. 访问应用
# 打开浏览器访问: http://localhost:5000
```

### 方法二：手动安装

```bash
# 1. 克隆LaMa项目
git clone https://github.com/advimman/lama.git /home/guojingpeng/workSpace/lama

# 2. 创建虚拟环境
cd /home/guojingpeng/workSpace/demo
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install --upgrade pip
pip install -r /home/guojingpeng/workSpace/lama/requirements.txt
pip install flask flask-cors opencv-python pillow numpy

# 4. 安装PyTorch
# CPU版本
pip install torch torchvision
# GPU版本（CUDA 10.2）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu102

# 5. 启动应用
python app.py
```

### 方法三：使用Docker

```bash
# 1. 构建Docker镜像
docker build -t lama-demo -f Dockerfile .

# 2. 运行容器
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/models:/app/models \
  --name lama-demo-container \
  lama-demo

# 3. 访问应用
# 打开浏览器访问: http://localhost:5000
```

## 使用指南

### 1. 上传图像
- 点击"选择文件"或拖拽图像到上传区域
- 支持格式: PNG, JPG, JPEG, BMP, TIFF, WEBP
- 文件大小限制: 最大50MB

### 2. 绘制掩码
- **画笔工具**: 自由绘制修复区域
- **矩形工具**: 绘制矩形修复区域
- **橡皮擦**: 擦除已绘制的区域
- **调整画笔大小**: 5-100像素
- **快捷键**: Ctrl+Z撤销，空格键拖动画布

### 3. 执行修复
- **标准修复**: 快速处理，适合一般场景
- **高质量修复**: 启用精炼算法，效果更好但耗时更长
- 处理时间: 通常10-90秒（取决于图像大小和质量选项）

### 4. 结果下载
- 点击"下载结果"保存修复后的图像
- 支持重新开始或复制结果链接

## API接口

### 状态检查
```bash
GET /api/status
```

### 上传图像
```bash
POST /api/upload
Content-Type: multipart/form-data
```

### 创建掩码
```bash
POST /api/create_mask
Content-Type: application/json
```

### 执行修复
```bash
POST /api/inpaint
Content-Type: application/json
```

### 下载结果
```bash
GET /api/download/<filename>
```

### 预览图像
```bash
GET /api/preview/<type>
# type: original, mask, result
```

### 清除数据
```bash
POST /api/clear
```

## 目录结构

```
demo/
├── app.py                    # Flask主应用
├── config.py                # 配置文件
├── start.sh                 # 启动脚本
├── stop.sh                  # 停止脚本
├── Dockerfile              # Docker构建文件
├── requirements.txt        # Python依赖
├── LaMa_分析报告.md        # 项目分析报告
├── 使用教程.md             # 详细使用教程
├── 技术文档.md             # 技术文档
├── static/                 # 静态文件
│   ├── css/
│   │   └── style.css      # 样式文件
│   └── js/
│       └── main.js        # 前端脚本
├── templates/              # 模板文件
│   └── index.html         # 主页面
└── logs/                  # 日志目录
```

## 配置选项

编辑 `config.py` 调整系统参数：

```python
class Config:
    # 上传设置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = '/tmp/lama_uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}
    
    # 模型设置
    MODEL_PATH = '/home/guojingpeng/workSpace/lama/big-lama'
    
    # 服务器设置
    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = True
```

## 常见问题

### Q1: 如何下载LaMa模型？
A: 可以从以下地址下载预训练模型：
- https://drive.google.com/drive/folders/1B2x7eQDgecTL0oh3LSIBDGj0fTxs6Ips
- https://huggingface.co/smartywu/big-lama

将模型解压到 `/home/guojingpeng/workSpace/lama/big-lama` 目录。

### Q2: 如何启用GPU加速？
A: 确保系统已安装CUDA和cuDNN，然后：
```bash
# 卸载CPU版本
pip uninstall torch torchvision -y

# 安装GPU版本（根据CUDA版本选择）
# CUDA 10.2
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu102
```

### Q3: 如何处理大尺寸图像？
A: 系统会自动调整图像到合适尺寸，最大支持2048×2048分辨率。对于更大图像，建议先进行预处理。

### Q4: 如何调整修复质量？
A: 在修复步骤中可以选择：
- **标准修复**: 快速，适合一般场景
- **高质量修复**: 使用精炼算法，效果更好但更耗时

## 性能优化

### 内存优化
- 限制图像最大尺寸为2048×2048
- 自动清理临时文件
- 使用内存缓存复用计算结果

### 处理速度
- 支持批处理提高效率
- 使用GPU加速（如有）
- 优化图像预处理流水线

## 故障排除

### 查看日志
```bash
# 实时查看日志
tail -f demo.log

# 查看错误信息
grep -i error demo.log
```

### 检查端口占用
```bash
# 检查端口5000是否被占用
lsof -i :5000

# 使用其他端口
./start.sh --port 8080
```

### 重置系统
```bash
# 停止服务
./stop.sh clean

# 重新启动
./start.sh
```

## 更新日志

### v1.0 (2026-03-21)
- 初始版本发布
- 支持图像上传、掩码绘制、修复处理
- 提供Web界面和API接口
- 支持Docker容器化部署

## 技术支持

- **GitHub Issues**: https://github.com/advimman/lama/issues
- **项目主页**: https://advimman.github.io/lama-project/
- **论文**: https://arxiv.org/abs/2109.07161

## 许可证

本项目基于LaMa项目的许可证，具体参见原项目LICENSE文件。

---

**开始使用**: [快速开始](#快速开始) | [使用指南](#使用指南) | [API接口](#api接口)