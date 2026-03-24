#!/usr/bin/env python3
"""
LaMa Web界面演示
使用Gradio创建交互式Web界面
"""

import os
import sys
import gradio as gr
from pathlib import Path
import tempfile
import numpy as np
from PIL import Image

# 添加lama项目到Python路径
lama_path = Path(__file__).parent.parent.parent / "lama"
sys.path.append(str(lama_path))

# 导入我们的演示类
try:
    from simple_demo import LaMaDemo
    DEMO_AVAILABLE = True
except ImportError:
    DEMO_AVAILABLE = False
    print("⚠️  无法导入LaMaDemo，使用模拟模式")


class LaMaWebDemo:
    """LaMa Web界面演示类"""
    
    def __init__(self):
        self.demo = None
        self._init_demo()
    
    def _init_demo(self):
        """初始化演示"""
        try:
            if DEMO_AVAILABLE:
                # 检查模型路径
                model_path = str(lama_path / "big-lama")
                if not os.path.exists(model_path):
                    # 尝试在demo目录查找
                    demo_model_path = Path(__file__).parent.parent / "models" / "big-lama"
                    if os.path.exists(demo_model_path):
                        model_path = str(demo_model_path)
                
                self.demo = LaMaDemo(model_path=model_path, device="cpu")
                print("✅ LaMa演示初始化成功")
            else:
                print("⚠️  使用模拟模式")
                self.demo = None
        except Exception as e:
            print(f"❌ 演示初始化失败: {e}")
            self.demo = None
    
    def process_image(self, image, mask, refine=False):
        """
        处理图像
        
        Args:
            image: 输入图像（PIL或numpy）
            mask: 掩码图像（PIL或numpy）
            refine: 是否使用精炼模式
            
        Returns:
            修复后的图像
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as img_file, \
             tempfile.NamedTemporaryFile(suffix=".png", delete=False) as mask_file:
            
            # 保存图像
            if isinstance(image, np.ndarray):
                image_pil = Image.fromarray(image)
            else:
                image_pil = image
            
            if isinstance(mask, np.ndarray):
                mask_pil = Image.fromarray(mask)
            else:
                mask_pil = mask
            
            image_pil.save(img_file.name)
            mask_pil.save(mask_file.name)
            
            # 处理图像
            if self.demo:
                result = self.demo.inpaint_single(
                    img_file.name,
                    mask_file.name,
                    refine=refine
                )
            else:
                # 模拟处理
                result = self._simulate_web_inpainting(image_pil, mask_pil, refine)
            
            # 清理临时文件
            os.unlink(img_file.name)
            os.unlink(mask_file.name)
            
            return result if result else image_pil
    
    def _simulate_web_inpainting(self, image, mask, refine=False):
        """
        模拟Web界面的图像修复（演示用）
        """
        # 转换为numpy数组
        image_np = np.array(image)
        mask_np = np.array(mask)
        
        # 确保mask是单通道
        if len(mask_np.shape) == 3:
            mask_np = mask_np[:, :, 0]
        
        # 创建一个副本
        result = image_np.copy()
        
        # 获取掩码区域
        mask_bool = mask_np > 128
        
        if mask_bool.any():
            # 模拟修复：使用周围像素填充
            height, width = image_np.shape[:2]
            
            # 使用简单的方法：用周围像素的平均值填充
            for i in range(height):
                for j in range(width):
                    if mask_bool[i, j]:
                        # 获取周围有效像素
                        neighbors = []
                        radius = 3
                        
                        for di in range(-radius, radius + 1):
                            for dj in range(-radius, radius + 1):
                                if di == 0 and dj == 0:
                                    continue
                                    
                                ni, nj = i + di, j + dj
                                if (0 <= ni < height and 0 <= nj < width and 
                                    not mask_bool[ni, nj]):
                                    neighbors.append(image_np[ni, nj])
                        
                        if neighbors:
                            # 使用周围像素的平均值
                            result[i, j] = np.mean(neighbors, axis=0).astype(np.uint8)
        
        return Image.fromarray(result)
    
    def create_interface(self):
        """创建Gradio界面"""
        
        # 示例图像
        examples = [
            ["./data/input/example1.jpg", "./data/masks/example1_mask.jpg"],
            ["./data/input/example2.jpg", "./data/masks/example2_mask.jpg"],
        ]
        
        # 检查示例文件是否存在
        actual_examples = []
        for img_path, mask_path in examples:
            full_img_path = Path(__file__).parent.parent / img_path
            full_mask_path = Path(__file__).parent.parent / mask_path
            
            if full_img_path.exists() and full_mask_path.exists():
                actual_examples.append([str(full_img_path), str(full_mask_path)])
        
        if not actual_examples:
            # 创建一些虚拟示例
            print("📝 创建虚拟示例图像...")
            self._create_example_images()
            actual_examples = [
                ["./data/input/example1.jpg", "./data/masks/example1_mask.jpg"],
                ["./data/input/example2.jpg", "./data/masks/example2_mask.jpg"],
            ]
        
        with gr.Blocks(title="LaMa 图像修复演示", theme=gr.themes.Soft()) as interface:
            gr.Markdown("# 🦙 LaMa 图像修复工具")
            gr.Markdown("""
            **LaMa** (Large Mask Inpainting with Fourier Convolutions) 是一个基于深度学习的图像修复工具。
            它可以智能地修复图像中的缺失部分，去除水印、文字或不需要的物体。
            
            ## 使用方法
            1. 上传需要修复的图像
            2. 上传或绘制掩码（白色区域表示需要修复的部分）
            3. 点击"开始修复"按钮
            4. 查看和下载修复结果
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    input_image = gr.Image(
                        label="输入图像",
                        type="pil",
                        height=400
                    )
                    
                    mask_image = gr.Image(
                        label="掩码图像",
                        type="pil",
                        source="upload",
                        tool="sketch",
                        height=400,
                        brush_color="white"
                    )
                    
                    refine_checkbox = gr.Checkbox(
                        label="使用精炼模式",
                        value=False,
                        info="精炼模式会产生更平滑的结果，但速度稍慢"
                    )
                    
                    process_btn = gr.Button("🚀 开始修复", variant="primary")
                
                with gr.Column(scale=1):
                    output_image = gr.Image(
                        label="修复结果",
                        type="pil",
                        height=400
                    )
                    
                    with gr.Row():
                        download_btn = gr.Button("📥 下载结果")
                        reset_btn = gr.Button("🔄 重置")
            
            # 示例部分
            with gr.Accordion("📚 查看示例", open=False):
                gr.Examples(
                    examples=actual_examples,
                    inputs=[input_image, mask_image],
                    outputs=[output_image],
                    fn=self.process_image,
                    cache_examples=False
                )
            
            # 事件处理
            process_btn.click(
                fn=self.process_image,
                inputs=[input_image, mask_image, refine_checkbox],
                outputs=output_image
            )
            
            reset_btn.click(
                fn=lambda: [None, None, None],
                outputs=[input_image, mask_image, output_image]
            )
            
            download_btn.click(
                fn=lambda img: img.save("laMa_result.png") if img else None,
                inputs=output_image
            )
            
            # 添加说明
            gr.Markdown("""
            ## 📝 使用技巧
            
            ### 关于掩码
            - 掩码图像应该是黑白图像
            - 白色区域表示需要修复的部分
            - 黑色区域表示保留不变的部分
            - 可以使用右侧的画笔工具直接绘制
            
            ### 最佳实践
            - 使用高质量输入图像
            - 确保掩码准确覆盖需要修复的区域
            - 对于大面积修复，建议使用精炼模式
            - 修复后可以进一步调整色彩和对比度
            
            ## ⚠️ 注意事项
            - 当前为演示模式，实际效果可能有所不同
            - 大图像可能需要较长时间处理
            - 建议图像分辨率不超过2K
            """)
        
        return interface
    
    def _create_example_images(self):
        """创建示例图像（演示用）"""
        data_dir = Path(__file__).parent.parent / "data"
        input_dir = data_dir / "input"
        mask_dir = data_dir / "masks"
        
        # 创建目录
        input_dir.mkdir(parents=True, exist_ok=True)
        mask_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建示例图像1
        img1 = Image.new("RGB", (512, 512), color=(100, 150, 200))
        mask1 = Image.new("L", (512, 512), color=0)
        
        # 在图像上添加一些内容
        from PIL import ImageDraw
        draw_img = ImageDraw.Draw(img1)
        draw_mask = ImageDraw.Draw(mask1)
        
        # 添加一个需要修复的矩形
        draw_img.rectangle([100, 100, 300, 300], fill=(200, 100, 50))
        draw_mask.rectangle([100, 100, 300, 300], fill=255)
        
        # 添加一些文字
        draw_img.text([150, 150], "修复我", fill=(255, 255, 255))
        
        # 保存
        img1.save(input_dir / "example1.jpg")
        mask1.save(mask_dir / "example1_mask.jpg")
        
        # 创建示例图像2
        img2 = Image.new("RGB", (512, 512), color=(50, 200, 150))
        mask2 = Image.new("L", (512, 512), color=0)
        
        draw_img2 = ImageDraw.Draw(img2)
        draw_mask2 = ImageDraw.Draw(mask2)
        
        # 添加一个圆形需要修复
        draw_img2.ellipse([150, 150, 350, 350], fill=(255, 100, 100))
        draw_mask2.ellipse([150, 150, 350, 350], fill=255)
        
        draw_img2.text([200, 250], "圆形修复", fill=(255, 255, 255))
        
        img2.save(input_dir / "example2.jpg")
        mask2.save(mask_dir / "example2_mask.jpg")
        
        print(f"✅ 创建了示例图像在: {data_dir}")


def main():
    """主函数"""
    # 创建Web演示
    web_demo = LaMaWebDemo()
    
    # 创建界面
    interface = web_demo.create_interface()
    
    # 启动服务
    print("🌐 启动Web界面...")
    print("   访问地址: http://localhost:7860")
    print("   按Ctrl+C停止服务")
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=False
    )


if __name__ == "__main__":
    main()