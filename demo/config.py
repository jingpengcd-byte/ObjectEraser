# LaMa演示系统配置

import os
from pathlib import Path

class Config:
    """基础配置类"""
    
    # 密钥设置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'lama-demo-secret-key-2026'
    
    # 上传设置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = '/tmp/lama_uploads'
    RESULT_FOLDER = '/tmp/lama_results'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}
    
    # 模型设置
    LAMA_PROJECT_PATH = '/home/guojingpeng/workSpace/lama'
    MODEL_PATH = os.path.join(LAMA_PROJECT_PATH, 'big-lama')
    
    # 修复设置
    ENABLE_REFINE = True
    REFINE_ITERATIONS = 15
    MAX_IMAGE_SIZE = 2048  # 最大图像尺寸
    
    # 服务器设置
    HOST = '0.0.0.0'
    PORT = 5001
    DEBUG = True
    THREADED = True
    
    @staticmethod
    def init_app(app):
        """初始化应用"""
        # 创建必要的目录
        for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULT_FOLDER']]:
            Path(folder).mkdir(parents=True, exist_ok=True)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # 生产环境日志设置
        import logging
        from logging.handlers import RotatingFileHandler
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 文件处理器
        file_handler = RotatingFileHandler(
            'demo.log', maxBytes=10485760, backupCount=10
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # 添加处理器到应用
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('LaMa演示系统启动')

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = False

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# 环境变量加载
def load_environment_variables():
    """从环境变量加载配置"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])