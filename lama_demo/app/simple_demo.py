#!/usr/bin/env python3
"""
LaMa Demo 工程 - 最简单的使用示例
这个文件展示了如何使用LaMa进行基本的图像修复
"""

import os
import sys
import argparse
from pathlib import Path

# 添加lama项目到Python路径
lama_path = Path(__file__).parent.parent.parent / "lama"
sys.path.append(str(lama_path))

import torch
import numpy as np
from PIL import Image
import cv2


class LaMaDemo:
    """LaMa图像修复演示类"""
    
    def __init__(self, model_path=None, device="cuda" if torch.cuda.is_available() else "cpu"):
        """
        初始化LaMa演示
        
        Args:
            model_path: 模型路径
            device: 计算设备 (cuda/cpu)
        """
        self.device = device
        
        # 设置环境变量
        os.environ["TORCH_HOME"] = str(lama_path)
        
        # 加载模型
        self.model_path = model_path or str(lama_path / "big-lama")
        self._load_model()
        
        print(f"✅ LaMa演示初始化完成，使用设备: {device}")
        print(f"   模型路径: {self.model_path}")
    
    def _load_model(self):
        """加载LaMa模型"""
        try:
            # 这里是简化的模型加载
            # 实际使用时需要根据lama项目的具体API进行调整
            print(f"正在加载模型: {self.model_path}")
            
            # 检查模型文件是否存在
            if not os.path.exists(self.model_path):
                print(f"⚠️  模型路径不存在: {self.model_path}")
                print("请先下载预训练模型:")
                print("  wget https://huggingface.co/smartywu/big-lama/resolve/main/big-lama.zip")
                print("  unzip big-lama.zip")
                return
            
            # 在实际项目中，这里会加载真正的模型
            # 为了演示，我们只创建占位符
            self.model_loaded = True
            print("✅ 模型加载成功（演示模式）")
            
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            self.model_loaded = False
    
    def inpaint_single(self, image_path, mask_path, output_path=None, refine=False):
        """
        修复单张图像
        
        Args:
            image_path: 输入图像路径
            mask_path: 掩码图像路径
            output_path: 输出路径（可选）
            refine: 是否使用精炼模式
            
        Returns:
            PIL.Image: 修复后的图像
        """
        if not self.model_loaded:
            print("❌ 模型未加载，无法进行修复")
            return None
        
        print(f"🔧 开始修复图像: {image_path}")
        print(f"   使用掩码: {mask_path}")
        print(f"   精炼模式: {refine}")
        
        try:
            # 读取图像
            image = Image.open(image_path).convert("RGB")
            mask = Image.open(mask_path).convert("L")
            
            # 检查图像和掩码尺寸是否匹配
            if image.size != mask.size:
                print(f"⚠️  图像和掩码尺寸不匹配: {image.size} != {mask.size}")
                print("正在调整掩码尺寸...")
                mask = mask.resize(image.size, Image.Resampling.NEAREST)
            
            # 转换为numpy数组
            image_np = np.array(image)
            mask_np = np.array(mask)
            
            # 在实际项目中，这里会调用真实的LaMa修复
            # 为了演示，我们生成一个模拟的修复结果
            result_np = self._simulate_inpainting(image_np, mask_np, refine)
            
            # 转换为PIL图像
            result = Image.fromarray(result_np)
            
            # 保存结果
            if output_path:
                result.save(output_path)
                print(f"✅ 结果已保存到: {output_path}")
            
            return result
            
        except Exception as e:
            print(f"❌ 图像修复失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _simulate_inpainting(self, image, mask, refine=False):
        """
        模拟图像修复过程（演示用）
        
        在实际项目中，这里应该调用真实的LaMa模型
        """
        print("🔧 正在模拟图像修复过程...")
        
        # 创建一个副本
        result = image.copy()
        
        # 获取掩码区域
        mask_bool = mask > 128
        
        if mask_bool.any():
            # 模拟修复：使用周围像素填充
            for i in range(image.shape[0]):
                for j in range(image.shape[1]):
                    if mask_bool[i, j]:
                        # 获取周围像素
                        neighbors = []
                        for di in [-1, 0, 1]:
                            for dj in [-1, 0, 1]:
                                ni, nj = i + di, j + dj
                                if (0 <= ni < image.shape[0] and 
                                    0 <= nj < image.shape[1] and 
                                    not mask_bool[ni, nj]):
                                    neighbors.append(image[ni, nj])
                        
                        if neighbors:
                            # 使用周围像素的平均值
                            result[i, j] = np.mean(neighbors, axis=0).astype(np.uint8)
        
        # 如果是精炼模式，添加一些后处理
        if refine:
            # 简单的模糊处理模拟精炼
            result = cv2.GaussianBlur(result, (3, 3), 0)
        
        return result
    
    def inpaint_batch(self, input_dir, mask_dir, output_dir):
        """
        批量修复图像
        
        Args:
            input_dir: 输入图像目录
            mask_dir: 掩码图像目录
            output_dir: 输出目录
        """
        print(f"🔧 开始批量修复:")
        print(f"   输入目录: {input_dir}")
        print(f"   掩码目录: {mask_dir}")
        print(f"   输出目录: {output_dir}")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取所有图像文件
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(Path(input_dir).glob(f"*{ext}"))
            image_files.extend(Path(input_dir).glob(f"*{ext.upper()}"))
        
        print(f"📁 找到 {len(image_files)} 个图像文件")
        
        success_count = 0
        
        for image_path in image_files:
            # 构建对应的掩码路径
            mask_name = image_path.stem + "_mask" + image_path.suffix
            mask_path = Path(mask_dir) / mask_name
            
            if not mask_path.exists():
                print(f"⚠️  找不到对应的掩码: {mask_path}")
                continue
            
            # 构建输出路径
            output_name = image_path.stem + "_inpainted" + image_path.suffix
            output_path = Path(output_dir) / output_name
            
            # 修复图像
            result = self.inpaint_single(
                str(image_path),
                str(mask_path),
                str(output_path)
            )
            
            if result is not None:
                success_count += 1
        
        print(f"✅ 批量修复完成:")
        print(f"   成功修复: {success_count}/{len(image_files)} 张图像")
        print(f"   输出目录: {output_dir}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LaMa图像修复演示")
    parser.add_argument("--input", type=str, help="输入图像路径")
    parser.add_argument("--mask", type=str, help="掩码图像路径")
    parser.add_argument("--output", type=str, default=None, help="输出图像路径")
    parser.add_argument("--input-dir", type=str, help="输入图像目录（批量处理）")
    parser.add_argument("--mask-dir", type=str, help="掩码图像目录（批量处理）")
    parser.add_argument("--output-dir", type=str, default="./output", help="输出目录")
    parser.add_argument("--device", type=str, default="cpu", help="计算设备 (cpu/cuda)")
    parser.add_argument("--refine", action="store_true", help="使用精炼模式")
    parser.add_argument("--model", type=str, default=None, help="模型路径")
    
    args = parser.parse_args()
    
    # 初始化LaMa演示
    demo = LaMaDemo(model_path=args.model, device=args.device)
    
    if args.input and args.mask:
        # 单张图像修复
        demo.inpaint_single(
            args.input,
            args.mask,
            args.output,
            args.refine
        )
    elif args.input_dir and args.mask_dir:
        # 批量图像修复
        demo.inpaint_batch(
            args.input_dir,
            args.mask_dir,
            args.output_dir
        )
    else:
        print("❌ 请提供输入参数")
        print("单张修复: --input <图像> --mask <掩码>")
        print("批量修复: --input-dir <输入目录> --mask-dir <掩码目录>")
        parser.print_help()


if __name__ == "__main__":
    main()