import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static/uploads')

    # 七牛云配置
    QINIU_ACCESS_KEY = os.environ.get('QINIU_ACCESS_KEY', 'your-access-key')
    QINIU_SECRET_KEY = os.environ.get('QINIU_SECRET_KEY', 'your-secret-key')
    QINIU_BUCKET_NAME = os.environ.get('QINIU_BUCKET_NAME', 'rwa-hub')
    QINIU_DOMAIN = os.environ.get('QINIU_DOMAIN', 'sqbw3uvy8.sabkt.gdipper.com')
    
    # 管理员配置
    ADMIN_CONFIG = {
        'super_admin': {
            'address': '0x6394993426DBA3b654eF0052698Fe9E0B6A98870',
            'role': 'super_admin',
            'name': '超级管理员',
            'level': 1,
            'permissions': ['审核', '编辑', '删除', '发布公告', '管理用户', '查看统计']
        },
        '0x124e5B8A4E6c68eC66e181E0B54817b12D879c57': {
            'role': '副管理员',
            'name': '副管理员',
            'permissions': ['审核', '编辑', '查看统计'],
            'level': 2  # 次级
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
    
    # 为了向后兼容，保留原有的管理员地址列表
    @property
    def ADMIN_ADDRESSES(self):
        return [admin['address'] if 'address' in admin else address for address, admin in self.ADMIN_CONFIG.items()]

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://rwa_hub_user:3YIeu6i1Nuyb6z8wRAxdctbMJVrSseJB@dpg-cu6b270gph6c73c50eag-a/rwa_hub'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def init_app(app):
        # 生产环境特定的配置
        pass

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 
