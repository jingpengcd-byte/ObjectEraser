#!/usr/bin/env python3
"""
LaMa图像修复演示系统 - Flask Web应用
"""

import os
import io
import sys
import json
import logging
import tempfile
import traceback
import threading
import time
import uuid
from pathlib import Path

# 添加LaMa项目路径
LAMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lama'))
sys.path.insert(0, LAMA_PATH)

import cv2
import numpy as np
from PIL import Image
import torch
from flask import Flask, render_template, request, jsonify, send_file, session, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 导入LaMa相关模块
from saicinpainting.evaluation.utils import move_to_device
from saicinpainting.evaluation.refinement import refine_predict
from saicinpainting.training.data.datasets import make_default_val_dataset
from saicinpainting.training.trainers import load_checkpoint

# 设置环境变量
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUM_EXPR_NUM_THREADS'] = '1'

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
log_file_path = os.path.join(os.path.dirname(__file__), 'demo.log')
if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', '') == log_file_path for h in logger.handlers):
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    logger.addHandler(file_handler)

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.secret_key = 'lama_demo_secret_key_2026'
CORS(app)

# 配置文件
app.config.update(
    MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 50MB最大文件大小
    UPLOAD_FOLDER=os.path.join(tempfile.gettempdir(), 'lama_uploads'),
    RESULT_FOLDER=os.path.join(tempfile.gettempdir(), 'lama_results'),
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'},
    MODEL_PATH=os.path.join(LAMA_PATH, 'big-lama'),  # 假设模型已下载
    AUTO_RESIZE_ENABLED=True,
    MAX_LONG_SIDE=1536,
    ROI_INFERENCE_ENABLED=True,
    ROI_PADDING=128,
)

# 创建必要的目录
for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULT_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

class LaMaInpainter:
    """LaMa图像修复器封装类"""
    
    def __init__(self, model_path=None):
        """初始化修复器"""
        self.model_path = model_path or app.config['MODEL_PATH']
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.train_config = None
        self.loaded = False
        
    def load_model(self):
        """加载模型"""
        if self.loaded:
            return True
            
        try:
            logger.info(f"加载模型: {self.model_path}")
            
            # 检查模型路径是否存在
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"模型路径不存在: {self.model_path}")
            
            # 加载训练配置
            train_config_path = os.path.join(self.model_path, 'config.yaml')
            if not os.path.exists(train_config_path):
                raise FileNotFoundError(f"配置文件不存在: {train_config_path}")
            
            import yaml
            from omegaconf import OmegaConf
            
            with open(train_config_path, 'r') as f:
                self.train_config = OmegaConf.create(yaml.safe_load(f))
            
            self.train_config.training_model.predict_only = True
            self.train_config.visualizer.kind = 'noop'
            
            # 加载检查点
            checkpoint_path = os.path.join(self.model_path, 'models', 'best.ckpt')
            if not os.path.exists(checkpoint_path):
                # 尝试其他可能的检查点名称
                checkpoints = [f for f in os.listdir(os.path.join(self.model_path, 'models')) 
                             if f.endswith('.ckpt')]
                if checkpoints:
                    checkpoint_path = os.path.join(self.model_path, 'models', checkpoints[0])
                else:
                    raise FileNotFoundError(f"未找到检查点文件: {checkpoint_path}")
            
            self.model = load_checkpoint(self.train_config, checkpoint_path, strict=False, map_location='cpu')
            self.model.freeze()
            self.model.to(self.device)
            
            self.loaded = True
            logger.info("模型加载成功")
            return True
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            traceback.print_exc()
            return False
    
    def predict_single(self, image_path, mask_path, refine=False, progress_callback=None, optimize_options=None):
        """对单个图像进行预测"""
        if not self.loaded and not self.load_model():
            raise RuntimeError("模型加载失败")
        if progress_callback:
            progress_callback(10, '模型已就绪')
        timings = {}
        optimize_options = optimize_options or {}
        auto_resize_enabled = bool(optimize_options.get('auto_resize_enabled', app.config['AUTO_RESIZE_ENABLED']))
        max_long_side = int(optimize_options.get('max_long_side', app.config['MAX_LONG_SIDE']))
        roi_inference_enabled = bool(optimize_options.get('roi_inference_enabled', app.config['ROI_INFERENCE_ENABLED']))
        roi_padding = int(optimize_options.get('roi_padding', app.config['ROI_PADDING']))
        total_start = time.perf_counter()
        
        try:
            # 创建临时目录处理单个图像
            import tempfile
            import shutil
            from torch.utils.data._utils.collate import default_collate
            
            temp_dir = tempfile.mkdtemp()
            try:
                stage_start = time.perf_counter()
                input_dir = os.path.join(temp_dir, 'input')
                os.makedirs(input_dir, exist_ok=True)
                if progress_callback:
                    progress_callback(25, '准备输入数据')
                
                # 复制图像和掩码到输入目录 (必须确保扩展名为PNG，且没有mask后缀才能被Dataset正确识别)
                # 原图片需要被重命名为 XXX.png
                # 掩码图片需要被重命名为 XXX_mask.png
                base_name = "image"
                img_new_path = os.path.join(input_dir, f"{base_name}.png")
                mask_new_path = os.path.join(input_dir, f"{base_name}_mask.png")
                
                img_bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
                if img_bgr is None:
                    raise ValueError(f"无法读取输入图像: {image_path}")

                mask_raw = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
                if mask_raw is None:
                    raise ValueError(f"无法读取掩码图像: {mask_path}")

                if len(mask_raw.shape) == 3 and mask_raw.shape[2] == 4:
                    mask_gray = mask_raw[:, :, 3]
                elif len(mask_raw.shape) == 3:
                    mask_gray = cv2.cvtColor(mask_raw, cv2.COLOR_BGR2GRAY)
                else:
                    mask_gray = mask_raw

                _, mask_binary = cv2.threshold(mask_gray, 1, 255, cv2.THRESH_BINARY)

                img_h, img_w = img_bgr.shape[:2]
                if mask_binary.shape[:2] != (img_h, img_w):
                    logger.info(f"预测前自动对齐尺寸: image={(img_h, img_w)}, mask={mask_binary.shape[:2]}")
                    mask_binary = cv2.resize(mask_binary, (img_w, img_h), interpolation=cv2.INTER_NEAREST)

                original_image_bgr = img_bgr.copy()
                has_mask = np.any(mask_binary > 0)
                roi_bbox = None
                if roi_inference_enabled and has_mask:
                    ys, xs = np.where(mask_binary > 0)
                    y_min, y_max = int(ys.min()), int(ys.max())
                    x_min, x_max = int(xs.min()), int(xs.max())
                    pad = max(0, roi_padding)
                    x1 = max(0, x_min - pad)
                    y1 = max(0, y_min - pad)
                    x2 = min(img_w, x_max + pad + 1)
                    y2 = min(img_h, y_max + pad + 1)
                    roi_bbox = (x1, y1, x2, y2)
                    img_bgr = img_bgr[y1:y2, x1:x2]
                    mask_binary = mask_binary[y1:y2, x1:x2]

                pre_scale_h, pre_scale_w = img_bgr.shape[:2]
                scale_factor = 1.0
                if auto_resize_enabled and max_long_side > 0:
                    long_side = max(pre_scale_h, pre_scale_w)
                    if long_side > max_long_side:
                        scale_factor = max_long_side / float(long_side)
                        resize_w = max(1, int(round(pre_scale_w * scale_factor)))
                        resize_h = max(1, int(round(pre_scale_h * scale_factor)))
                        img_bgr = cv2.resize(img_bgr, (resize_w, resize_h), interpolation=cv2.INTER_AREA)
                        mask_binary = cv2.resize(mask_binary, (resize_w, resize_h), interpolation=cv2.INTER_NEAREST)

                cv2.imwrite(img_new_path, img_bgr)
                cv2.imwrite(mask_new_path, mask_binary)
                timings['prepare_input_sec'] = round(time.perf_counter() - stage_start, 3)
                if progress_callback:
                    progress_callback(40, '构建推理批次')
                
                stage_start = time.perf_counter()
                dataset = make_default_val_dataset(
                    input_dir,
                    img_suffix='.png',
                    pad_out_to_modulo=8
                )
                
                if len(dataset) == 0:
                    raise ValueError("未找到有效的图像-掩码对，请检查数据集路径和文件命名格式")
                
                # 进行预测
                batch = default_collate([dataset[0]])
                image_hw = batch['image'].shape[-2:]
                mask_hw = batch['mask'].shape[-2:]
                if image_hw != mask_hw:
                    logger.info(f"批次尺寸不一致，自动对齐: image={image_hw}, mask={mask_hw}")
                    batch['mask'] = torch.nn.functional.interpolate(
                        batch['mask'].float(),
                        size=image_hw,
                        mode='nearest'
                    )
                timings['build_batch_sec'] = round(time.perf_counter() - stage_start, 3)
                if progress_callback:
                    progress_callback(55, '开始模型推理')
                
                stage_start = time.perf_counter()
                if refine:
                    # 使用精炼算法
                    assert 'unpad_to_size' in batch, "需要未填充尺寸以进行精炼"
                    cur_res = refine_predict(batch, self.model, 
                                           gpu_ids='0' if torch.cuda.is_available() else '',
                                           modulo=8,
                                           n_iters=15,
                                           lr=0.002,
                                           min_side=512,
                                           max_scales=3,
                                           px_budget=1800000)
                    cur_res = cur_res[0].permute(1,2,0).detach().cpu().numpy()
                else:
                    # 标准预测
                    with torch.no_grad():
                        batch = move_to_device(batch, self.device)
                        batch['mask'] = (batch['mask'] > 0) * 1
                        batch = self.model(batch)
                        cur_res = batch['inpainted'][0].permute(1,2,0).detach().cpu().numpy()
                        
                        # 裁剪到原始尺寸
                        unpad_to_size = batch.get('unpad_to_size', None)
                        if unpad_to_size is not None:
                            orig_height, orig_width = unpad_to_size
                            cur_res = cur_res[:orig_height, :orig_width]
                timings['inference_sec'] = round(time.perf_counter() - stage_start, 3)
                if progress_callback:
                    progress_callback(85, '后处理结果')
                
                stage_start = time.perf_counter()
                if scale_factor != 1.0:
                    cur_res = cv2.resize(cur_res, (pre_scale_w, pre_scale_h), interpolation=cv2.INTER_LINEAR)

                if roi_bbox is not None:
                    x1, y1, x2, y2 = roi_bbox
                    if cur_res.shape[:2] != (y2 - y1, x2 - x1):
                        cur_res = cv2.resize(cur_res, (x2 - x1, y2 - y1), interpolation=cv2.INTER_LINEAR)
                    full_rgb = cv2.cvtColor(original_image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                    full_rgb[y1:y2, x1:x2] = cur_res
                    cur_res = full_rgb

                cur_res = np.clip(cur_res * 255, 0, 255).astype('uint8')
                cur_res = cv2.cvtColor(cur_res, cv2.COLOR_RGB2BGR)
                
                result_path = os.path.join(app.config['RESULT_FOLDER'], f"temp_result_{next(tempfile._get_candidate_names())}.png")
                cv2.imwrite(result_path, cur_res)
                timings['postprocess_save_sec'] = round(time.perf_counter() - stage_start, 3)
                timings['total_sec'] = round(time.perf_counter() - total_start, 3)
                if progress_callback:
                    progress_callback(100, '推理完成')
                
                return {
                    'result_path': result_path,
                    'timings': timings
                }
                
            finally:
                # 清理临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            logger.error(f"预测失败: {e}")
            traceback.print_exc()
            raise
    
    def predict_batch(self, input_dir, output_dir, refine=False):
        """批量预测"""
        if not self.loaded and not self.load_model():
            raise RuntimeError("模型加载失败")
        
        try:
            # 这里可以扩展为批量处理
            # 目前只处理单个文件，批量处理逻辑类似
            pass
            
        except Exception as e:
            logger.error(f"批量预测失败: {e}")
            raise

# 全局修复器实例
inpainter = None
inpaint_jobs = {}
inpaint_jobs_lock = threading.Lock()

def get_inpainter():
    """获取或创建修复器实例"""
    global inpainter
    if inpainter is None:
        inpainter = LaMaInpainter()
    return inpainter


def update_inpaint_job(job_id, **kwargs):
    with inpaint_jobs_lock:
        job = inpaint_jobs.get(job_id)
        if not job:
            return
        job.update(kwargs)
        job['updated_at'] = time.time()

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def create_mask_from_points(image_shape, points, brush_size=20):
    """从点创建掩码"""
    mask = np.zeros(image_shape[:2], dtype=np.uint8)
    
    for point in points:
        x, y = int(point['x']), int(point['y'])
        cv2.circle(mask, (x, y), brush_size, 255, -1)
    
    return mask

def create_mask_from_rect(image_shape, rect):
    """从矩形创建掩码"""
    mask = np.zeros(image_shape[:2], dtype=np.uint8)
    x1, y1, x2, y2 = rect
    cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
    return mask

@app.route('/')
def index():
    """主页"""
    return render_template('index.html', asset_version=str(int(time.time())))

@app.route('/api/status')
def api_status():
    """API状态检查"""
    inpainter = get_inpainter()
    model_loaded = inpainter.loaded
    
    return jsonify({
        'status': 'ok',
        'model_loaded': model_loaded,
        'device': str(inpainter.device) if inpainter else None,
        'has_cuda': torch.cuda.is_available()
    })

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """上传图像"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件部分'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if file and allowed_file(file.filename):
            # 保存文件
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # 读取图像信息
            img = cv2.imread(filepath)
            if img is None:
                return jsonify({'error': '无法读取图像文件'}), 400
            
            height, width = img.shape[:2]
            
            # 保存到session
            session['uploaded_image'] = filepath
            
            return jsonify({
                'status': 'ok',
                'filename': filename,
                'filepath': filepath,
                'width': width,
                'height': height,
                'size': os.path.getsize(filepath)
            })
        
        return jsonify({'error': '不允许的文件类型'}), 400
        
    except Exception as e:
        logger.error(f"上传失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/create_mask', methods=['POST'])
def api_create_mask():
    """创建掩码"""
    try:
        if 'mask' not in request.files:
            return jsonify({'error': '没有收到掩码文件'}), 400
            
        mask_file = request.files['mask']
        if mask_file.filename == '':
            return jsonify({'error': '掩码文件名为空'}), 400
            
        image_path = session.get('uploaded_image')
        if not image_path or not os.path.exists(image_path):
            return jsonify({'error': '请先上传图像'}), 400
            
        # 掩码统一保存为 png，避免原图扩展名导致 imwrite 编码器不可用
        image_stem = os.path.splitext(os.path.basename(image_path))[0]
        mask_filename = f"mask_{image_stem}.png"
        mask_path = os.path.join(app.config['UPLOAD_FOLDER'], mask_filename)
        mask_file.save(mask_path)
        
        # 验证掩码并处理alpha通道（前端canvas可能带有透明度）
        mask_img = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
        if mask_img is None:
            return jsonify({'error': '掩码文件损坏'}), 400
            
        # 如果是RGBA，提取Alpha通道或处理为灰度图
        if len(mask_img.shape) == 3 and mask_img.shape[2] == 4:
            # 使用Alpha通道作为掩码，有颜色的地方是255，透明的地方是0
            mask_gray = mask_img[:, :, 3]
        else:
            # 否则转换为灰度
            mask_gray = cv2.cvtColor(mask_img, cv2.COLOR_BGR2GRAY) if len(mask_img.shape) == 3 else mask_img
            
        # 确保掩码是二值图 (0 or 255)
        _, binary_mask = cv2.threshold(mask_gray, 1, 255, cv2.THRESH_BINARY)

        original_img = cv2.imread(image_path)
        if original_img is None:
            return jsonify({'error': '原始图像读取失败'}), 400
        orig_h, orig_w = original_img.shape[:2]
        if binary_mask.shape[:2] != (orig_h, orig_w):
            logger.info(f"掩码尺寸与原图不一致，自动缩放: mask={binary_mask.shape[:2]}, image={(orig_h, orig_w)}")
            binary_mask = cv2.resize(binary_mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)

        if not cv2.imwrite(mask_path, binary_mask):
            return jsonify({'error': f'掩码写入失败: {mask_path}'}), 500
        
        session['mask_path'] = mask_path
        
        return jsonify({
            'status': 'ok',
            'mask_path': mask_path,
            'mask_size': binary_mask.shape
        })
        
    except Exception as e:
        logger.error(f"创建掩码失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inpaint', methods=['POST'])
def api_inpaint():
    """执行修复"""
    try:
        data = request.json
        refine = data.get('refine', False) if data else False
        optimize_options = {
            'auto_resize_enabled': data.get('auto_resize_enabled', app.config['AUTO_RESIZE_ENABLED']) if data else app.config['AUTO_RESIZE_ENABLED'],
            'max_long_side': data.get('max_long_side', app.config['MAX_LONG_SIDE']) if data else app.config['MAX_LONG_SIDE'],
            'roi_inference_enabled': data.get('roi_inference_enabled', app.config['ROI_INFERENCE_ENABLED']) if data else app.config['ROI_INFERENCE_ENABLED'],
            'roi_padding': data.get('roi_padding', app.config['ROI_PADDING']) if data else app.config['ROI_PADDING'],
        }
        
        # 优先从请求中获取路径，否则使用 session (兼容跨域或session丢失)
        image_path = data.get('image_path') or session.get('uploaded_image')
        mask_path = data.get('mask_path') or session.get('mask_path')
        
        if not image_path or not os.path.exists(image_path):
            return jsonify({'error': '请先上传图像或图像已过期'}), 400
        
        if not mask_path or not os.path.exists(mask_path):
            return jsonify({'error': '请先创建掩码或掩码已过期'}), 400
        
        # 执行修复
        inpainter = get_inpainter()
        predict_output = inpainter.predict_single(image_path, mask_path, refine=refine, optimize_options=optimize_options)
        result_path = predict_output['result_path'] if isinstance(predict_output, dict) else predict_output
        timings = predict_output.get('timings', {}) if isinstance(predict_output, dict) else {}
        
        if not os.path.exists(result_path):
            return jsonify({'error': '修复结果不存在'}), 500
        
        # 保存结果路径
        result_filename = f"result_{os.path.splitext(os.path.basename(image_path))[0]}.png"
        final_result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        
        import shutil
        shutil.copy(result_path, final_result_path)
        if os.path.exists(result_path):
            os.remove(result_path)
        
        session['result_path'] = final_result_path
        
        return jsonify({
            'status': 'ok',
            'result_path': final_result_path,
            'timings': timings
        })
        
    except Exception as e:
        logger.error(f"修复失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/inpaint/start', methods=['POST'])
def api_inpaint_start():
    try:
        data = request.json or {}
        refine = data.get('refine', False)
        optimize_options = {
            'auto_resize_enabled': data.get('auto_resize_enabled', app.config['AUTO_RESIZE_ENABLED']),
            'max_long_side': data.get('max_long_side', app.config['MAX_LONG_SIDE']),
            'roi_inference_enabled': data.get('roi_inference_enabled', app.config['ROI_INFERENCE_ENABLED']),
            'roi_padding': data.get('roi_padding', app.config['ROI_PADDING']),
        }
        image_path = data.get('image_path') or session.get('uploaded_image')
        mask_path = data.get('mask_path') or session.get('mask_path')

        if not image_path or not os.path.exists(image_path):
            return jsonify({'error': '请先上传图像或图像已过期'}), 400
        if not mask_path or not os.path.exists(mask_path):
            return jsonify({'error': '请先创建掩码或掩码已过期'}), 400

        job_id = uuid.uuid4().hex
        with inpaint_jobs_lock:
            inpaint_jobs[job_id] = {
                'status': 'queued',
                'progress': 0,
                'message': '任务排队中',
                'error': None,
                'result_path': None,
                'timings': None,
                'optimize_options': optimize_options,
                'created_at': time.time(),
                'updated_at': time.time(),
            }
        logger.info(f"创建修复任务: job_id={job_id}, refine={refine}, options={optimize_options}")

        def run_job():
            try:
                update_inpaint_job(job_id, status='running', progress=5, message='开始执行')
                local_inpainter = get_inpainter()

                def on_progress(progress, message):
                    update_inpaint_job(job_id, status='running', progress=progress, message=message)

                predict_output = local_inpainter.predict_single(
                    image_path=image_path,
                    mask_path=mask_path,
                    refine=refine,
                    progress_callback=on_progress,
                    optimize_options=optimize_options
                )
                result_path = predict_output['result_path'] if isinstance(predict_output, dict) else predict_output
                timings = predict_output.get('timings', {}) if isinstance(predict_output, dict) else {}

                if not os.path.exists(result_path):
                    raise RuntimeError('修复结果不存在')

                result_filename = f"result_{os.path.splitext(os.path.basename(image_path))[0]}_{job_id[:8]}.png"
                final_result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
                import shutil
                shutil.copy(result_path, final_result_path)
                if os.path.exists(result_path):
                    os.remove(result_path)

                update_inpaint_job(
                    job_id,
                    status='done',
                    progress=100,
                    message='修复完成',
                    result_path=final_result_path,
                    timings=timings
                )
                logger.info(f"修复任务完成: job_id={job_id}, result={final_result_path}, timings={timings}")
            except Exception as ex:
                logger.error(f"异步修复失败: {ex}")
                update_inpaint_job(job_id, status='error', progress=100, message='修复失败', error=str(ex))

        threading.Thread(target=run_job, daemon=True).start()
        return jsonify({'status': 'ok', 'job_id': job_id})
    except Exception as e:
        logger.error(f"启动修复任务失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/inpaint/status/<job_id>', methods=['GET'])
def api_inpaint_status(job_id):
    with inpaint_jobs_lock:
        job = inpaint_jobs.get(job_id)
        if not job:
            return jsonify({'error': '任务不存在'}), 404
        return jsonify({
            'status': 'ok',
            'job_status': job['status'],
            'progress': job['progress'],
            'message': job['message'],
            'error': job['error'],
            'result_path': job['result_path'],
            'timings': job.get('timings'),
            'optimize_options': job.get('optimize_options'),
            'result_url': url_for('api_inpaint_result', job_id=job_id) if job.get('result_path') else None,
        })


@app.route('/api/inpaint/result/<job_id>', methods=['GET'])
def api_inpaint_result(job_id):
    with inpaint_jobs_lock:
        job = inpaint_jobs.get(job_id)
        if not job:
            return jsonify({'error': '任务不存在'}), 404
        result_path = job.get('result_path')
    if not result_path or not os.path.exists(result_path):
        return jsonify({'error': '结果不存在'}), 404
    as_attachment = request.args.get('download', '0') == '1'
    return send_file(result_path, as_attachment=as_attachment, download_name=os.path.basename(result_path))

@app.route('/api/download/<path:filename>')
def api_download(filename):
    """下载文件"""
    try:
        filepath = os.path.join(app.config['RESULT_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404
        
        as_attachment = request.args.get('download', '1') != '0'
        return send_file(filepath, as_attachment=as_attachment, download_name=os.path.basename(filepath))
        
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/preview/<type>')
def api_preview(type):
    """预览图像"""
    try:
        if type == 'original':
            filepath = session.get('uploaded_image')
        elif type == 'mask':
            filepath = session.get('mask_path')
        elif type == 'result':
            filepath = session.get('result_path')
        else:
            return jsonify({'error': '无效的预览类型'}), 400
        
        if not filepath or not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404
        
        # 读取图像并转换为base64
        with open(filepath, 'rb') as f:
            image_data = f.read()
        
        import base64
        encoded = base64.b64encode(image_data).decode('utf-8')
        
        return jsonify({
            'status': 'ok',
            'data': f'data:image/png;base64,{encoded}'
        })
        
    except Exception as e:
        logger.error(f"预览失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear', methods=['POST'])
def api_clear():
    """清除会话数据"""
    try:
        # 删除临时文件
        for key in ['uploaded_image', 'mask_path', 'result_path']:
            filepath = session.get(key)
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
        
        # 清除session
        session.clear()
        
        return jsonify({'status': 'ok', 'message': '已清除所有数据'})
        
    except Exception as e:
        logger.error(f"清除失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    """404错误处理"""
    return jsonify({'error': '页面不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"服务器错误: {error}")
    return jsonify({'error': '服务器内部错误'}), 500

if __name__ == '__main__':
    # 初始化修复器
    inpainter = get_inpainter()
    if not inpainter.load_model():
        logger.warning("模型加载失败，部分功能可能不可用")
    
    # 启动服务器
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True, use_reloader=False)
