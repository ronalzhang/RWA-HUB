import os

class Config:
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError('DATABASE_URL environment variable is not set')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 应用配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    
    # 七牛云配置
    QINIU_ACCESS_KEY = os.environ.get('QINIU_ACCESS_KEY')
    QINIU_SECRET_KEY = os.environ.get('QINIU_SECRET_KEY')
    QINIU_BUCKET_NAME = os.environ.get('QINIU_BUCKET_NAME')
    QINIU_DOMAIN = os.environ.get('QINIU_DOMAIN')
    
    # 管理员配置
    ADMIN_CONFIG = {
        '0x6394993426dba3b654ef0052698fe9e0b6a98870': {
            'role': 'super_admin',
            'permissions': ['all']
        }
    }
    
    # 权限等级说明
    PERMISSION_LEVELS = {
        '审核': 2,    # 副管理员及以上可审核
        '编辑': 2,    # 副管理员及以上可编辑
        '删除': 1,    # 仅主管理员可删除
        '发布公告': 1,  # 仅主管理员可发布公告
        '管理用户': 1,  # 仅主管理员可管理用户
        '查看统计': 2   # 副管理员及以上可查看统计
    }
    
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static/uploads')
    
    @staticmethod
    def init_app(app):
        # 基础配置初始化
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        # 开发环境特定的配置
        pass

class ProductionConfig(Config):
    DEBUG = False
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        # 生产环境特定的配置
        if os.environ.get('DATABASE_URL'):
            if os.environ.get('DATABASE_URL').startswith('postgres://'):
                os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql://', 1)
        pass

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 
