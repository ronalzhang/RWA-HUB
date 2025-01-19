import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # 安全配置
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # 管理员配置
    ADMIN_CONFIG = {
        # 超级管理员地址
        'super_admin': {
            'address': '0x6394993426DBA3b654eF0052698Fe9E0B6A98870',
            'role': 'super_admin',
            'name': '超级管理员',
            'level': 1,
            'permissions': ['审核', '编辑', '删除']
        }
    }
    
    # 权限等级配置
    PERMISSION_LEVELS = {
        '审核': 1,  # 需要超级管理员权限
        '编辑': 1,  # 需要超级管理员权限
        '删除': 1,  # 需要超级管理员权限
        '查看': 2   # 普通管理员即可
    }
    
    # 权限角色配置
    ROLE_PERMISSIONS = {
        'super_admin': ['审核', '编辑', '删除', '查看'],  # 超级管理员拥有所有权限
        'admin': ['查看', '编辑']  # 普通管理员只能查看和编辑
    }

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///instance/app.db'

class ProductionConfig(Config):
    DEBUG = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # 处理数据库 URL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError('Production environment requires DATABASE_URL to be set')
            
        # 处理 Render 特定的 postgres:// URL
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        cls.SQLALCHEMY_DATABASE_URI = database_url
    
    # 生产环境特定配置
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
