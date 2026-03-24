# LaMa Demo 工程使用教程

## 📚 快速开始

### 1. 环境设置

```bash
# 进入demo目录
cd /home/guojingpeng/workSpace/lama_demo

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装基础依赖
pip install torch torchvision torchaudio
pip install opencv-python pillow numpy matplotlib tqdm
pip install flask gradio requests
```

### 2. 下载预训练模型

```bash
# 进入lama项目目录
cd /home/guojingpeng/workSpace/lama

# 设置环境变量
export TORCH_HOME=$(pwd) && export PYTHONPATH=$(pwd)

# 下载模型（如果尚未下载）
wget https://huggingface.co/smartywu/big-lama/resolve/main/big-lama.zip
unzip big-lama.zip -d ../lama_demo/models/
```

### 3. 运行演示

#### 方式一：简单命令行演示
```bash
cd /home/guojingpeng/workSpace/lama_demo
python app/simple_demo.py
```

#### 方式二：Web界面演示
```bash
cd /home/guojingpeng/workSpace/lama_demo
python app/web_demo.py
```

#### 方式三：REST API演示
```bash
cd /home/guojingpeng/workSpace/lama_demo
python app/api_demo.py
```

## 🎯 Demo工程结构说明

### 核心文件
```
lama_demo/
├── app/
│   ├── simple_demo.py      # 最简单的使用示例
│   ├── web_demo.py         # 网页界面演示
│   ├── api_demo.py         # REST API服务
│   └── utils.py            # 工具函数
├── config/
│   ├── demo_config.yaml    # 演示配置
│   └── paths_config.yaml   # 路径配置
├── data/
│   ├── input/              # 输入图像（示例）
│   ├── masks/              # 掩码图像（示例）
│   └── output/             # 输出结果
├── models/
│   └── big-lama/           # 预训练模型
├── scripts/
│   ├── setup_demo.sh       # 一键设置脚本
│   └── run_all_demos.sh    # 运行所有演示
└── README.md              # 本文件
```

## 🔧 详细使用指南

### 1. 准备数据

#### 1.1 测试图像
将需要修复的图像放入 `data/input/` 目录

#### 1.2 创建掩码
掩码是白色区域表示需要修复的部分：
```python
from PIL import Image, ImageDraw
import numpy as np

# 创建矩形掩码
image = Image.open("input.jpg")
mask = Image.new("L", image.size, 0)
draw = ImageDraw.Draw(mask)
draw.rectangle([100, 100, 300, 300], fill=255)  # 白色矩形区域
mask.save("mask.png")
```

### 2. 使用LaMa进行修复

#### 2.1 基本使用
```python
import sys
sys.path.append("/home/guojingpeng/workSpace/lama")

from lama_demo.app.simple_demo import LaMaDemo

# 初始化
demo = LaMaDemo(model_path="../models/big-lama")

# 单张图像修复
result = demo.inpaint_single(
    image_path="data/input/test.jpg",
    mask_path="data/masks/test_mask.png",
    output_path="data/output/result.jpg"
)

# 批量处理
demo.inpaint_batch(
    input_dir="data/input/",
    mask_dir="data/masks/",
    output_dir="data/output/"
)
```

#### 2.2 高级功能
```python
# 调整参数
result = demo.inpaint_single(
    image_path="input.jpg",
    mask_path="mask.png",
    output_path="output.jpg",
    refine=True,           # 使用精炼模式
    device="cuda",         # 使用GPU
    batch_size=4           # 批处理大小
)

# 评估结果
metrics = demo.evaluate_result(
    original_path="input.jpg",
    result_path="output.jpg",
    mask_path="mask.png"
)
print(f"PSNR: {metrics['psnr']}, SSIM: {metrics['ssim']}")
```

### 3. 不同界面使用

#### 3.1 命令行界面
```bash
# 修复单张图像
python app/simple_demo.py --input data/input/test.jpg --mask data/masks/test_mask.png

# 修复目录中的所有图像
python app/simple_demo.py --input-dir data/input --mask-dir data/masks --output-dir data/output

# 使用GPU加速
python app/simple_demo.py --input test.jpg --mask mask.png --device cuda
```

#### 3.2 Web界面
```bash
# 启动Web界面（默认端口7860）
python app/web_demo.py

# 指定端口
python app/web_demo.py --port 8080

# 外部访问
python app/web_demo.py --server-name 0.0.0.0 --port 7860
```

访问 http://localhost:7860 使用图形界面

#### 3.3 REST API
```bash
# 启动API服务
python app/api_demo.py

# 使用curl测试
curl -X POST http://localhost:8000/inpaint \
  -F "image=@test.jpg" \
  -F "mask=@mask.png" \
  -o result.jpg
```

## 🚀 一键脚本

### 1. 完整设置脚本
```bash
# 运行一键设置
bash scripts/setup_demo.sh

# 脚本会自动：
# 1. 创建虚拟环境
# 2. 安装所有依赖
# 3. 下载预训练模型
# 4. 准备示例数据
# 5. 启动演示
```

### 2. 运行所有演示
```bash
bash scripts/run_all_demos.sh

# 脚本会依次启动：
# 1. 命令行演示
# 2. Web界面演示
# 3. API服务演示
```

## 📊 性能优化

### 1. GPU加速
```python
# 使用GPU
demo = LaMaDemo(device="cuda")

# 多GPU支持
demo = LaMaDemo(device="cuda:0,1")
```

### 2. 批处理优化
```python
# 调整批处理大小
demo = LaMaDemo(batch_size=8)  # 根据GPU内存调整

# 使用半精度
demo = LaMaDemo(use_fp16=True)
```

### 3. 内存优化
```python
# 减少内存占用
demo = LaMaDemo(
    max_resolution=1024,  # 限制最大分辨率
    use_checkpoint=True   # 使用梯度检查点
)
```

## 🔍 故障排除

### 常见问题1：找不到模型
```
解决方法：
1. 检查模型路径：ls /home/guojingpeng/workSpace/lama_demo/models/
2. 重新下载模型：bash scripts/download_models.sh
```

### 常见问题2：内存不足
```
解决方法：
1. 减少批处理大小：--batch-size 1
2. 降低分辨率：--max-size 512
3. 使用CPU：--device cpu
```

### 常见问题3：依赖冲突
```
解决方法：
1. 重新创建虚拟环境
2. 按顺序安装依赖
3. 使用requirements.txt中的版本
```

## 🎨 示例用例

### 1. 去除水印
```python
# 水印通常位于固定位置
mask = create_watermark_mask(image_size, watermark_position)
result = demo.inpaint_single(image, mask)
```

### 2. 修复老照片
```python
# 自动检测划痕和污渍
scratches = detect_scratches(old_photo)
result = demo.inpaint_single(old_photo, scratches)
```

### 3. 物体移除
```python
# 手动选择要移除的物体
selected_object = select_object_interactive(image)
result = demo.inpaint_single(image, selected_object_mask)
```

## 📈 性能测试

运行性能测试脚本：
```bash
python scripts/benchmark.py \
  --model big-lama \
  --input data/input/ \
  --device cuda \
  --batch-sizes 1 2 4 8
```

测试结果包括：
- 单张图像处理时间
- 内存使用情况
- 不同批处理大小的吞吐量

## 🤝 集成其他工具

### 1. 与OpenCV集成
```python
import cv2
from lama_demo.app.utils import LaMaWrapper

# 实时视频修复
cap = cv2.VideoCapture(0)
lama = LaMaWrapper()

while True:
    ret, frame = cap.read()
    # 检测并修复特定区域
    result = lama.inpaint_frame(frame)
    cv2.imshow('Result', result)
```

### 2. 与图像处理流水线集成
```python
from PIL import Image
from lama_demo.app.pipeline import ImageProcessingPipeline

pipeline = ImageProcessingPipeline([
    ('resize', {'size': (512, 512)}),
    ('inpaint', {'model': 'big-lama'}),
    ('enhance', {'method': 'sharpen'})
])

result = pipeline.process("input.jpg")
```

## 📱 移动端使用

### 1. 模型转换
```bash
# 转换为ONNX格式
python scripts/convert_to_onnx.py \
  --model big-lama \
  --output models/big-lama.onnx

# 转换为TensorFlow格式
python scripts/convert_to_tf.py \
  --model big-lama \
  --output models/big-lama.pb
```

### 2. 移动端集成示例
```python
# Android示例（使用TensorFlow Lite）
import tflite_runtime.interpreter as tflite

interpreter = tflite.Interpreter(model_path="models/big-lama.tflite")
# ... 移动端推理代码
```

## 🎯 最佳实践

### 1. 数据准备
- 使用高质量输入图像
- 确保掩码准确覆盖需要修复的区域
- 预处理图像（调整大小、归一化）

### 2. 参数调优
- 根据图像内容选择合适的模型
- 调整修复强度参数
- 使用精炼模式提高质量

### 3. 结果后处理
- 对修复结果进行色彩校正
- 使用边缘保持平滑
- 融合原始图像和修复结果

## 📞 技术支持

遇到问题请检查：
1. 日志文件：`logs/demo.log`
2. 错误信息：控制台输出
3. 文档：本README和各脚本的注释

或联系技术支持：
- 邮箱：support@example.com
- GitHub Issues：项目仓库

---

**祝你使用愉快！** 🎉

这个LaMa Demo工程已经包含了所有必要的组件，让你可以快速开始使用这个强大的图像修复工具。