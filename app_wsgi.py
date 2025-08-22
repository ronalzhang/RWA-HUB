import os
import sys
from multiprocessing import cpu_count
from gunicorn.app.base import BaseApplication
from app import create_app

# 从旧文件中保留此函数，以确保环境变量和配置在Gunicorn worker中正确加载
def load_encrypted_config(app_context):
    """启动时加载加密的配置"""
    with app_context:
        try:
            from app.models.admin import SystemConfig
            from app.utils.crypto_manager import get_crypto_manager
            
            encrypted_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY_ENCRYPTED')
            encrypted_password = SystemConfig.get_value('CRYPTO_PASSWORD_ENCRYPTED')
            
            if encrypted_key and encrypted_password:
                original_password = os.environ.get('CRYPTO_PASSWORD')
                os.environ['CRYPTO_PASSWORD'] = 'RWA_HUB_SYSTEM_KEY_2024'
                
                try:
                    system_crypto = get_crypto_manager()
                    crypto_password = system_crypto.decrypt_private_key(encrypted_password)
                    
                    os.environ['CRYPTO_PASSWORD'] = crypto_password
                    os.environ['SOLANA_PRIVATE_KEY_ENCRYPTED'] = encrypted_key
                    
                    print("✅ 成功加载加密的私钥配置")
                    
                except Exception as e:
                    print(f"❌ 加载加密配置失败: {e}")
                    if original_password:
                        os.environ['CRYPTO_PASSWORD'] = original_password
            else:
                print("ℹ️  未找到加密的私钥配置，将使用环境变量中的配置")
                
        except Exception as e:
            print(f"❌ 加载加密配置时出错: {e}")

# 创建应用实例
flask_app = create_app()

# 在Gunicorn启动前，确保配置已加载
with flask_app.app_context():
    db_uri = os.environ.get('DATABASE_URL', 'postgresql://rwa_hub_user:password@localhost/rwa_hub')
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    try:
        load_encrypted_config(flask_app.app_context())
    except Exception as e:
        print(f"警告: 无法加载加密配置: {e}")


class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

def main():
    host = os.environ.get('HOST', '0.0.0.0')
    port = os.environ.get('PORT', '9000')
    # 根据CPU核心数动态设置worker数量
    workers = (cpu_count() * 2) + 1

    options = {
        'bind': f'{host}:{port}',
        'workers': workers,
        'worker_class': 'gevent', # 使用gevent以获得更好的性能
        'timeout': 120, # 增加超时以处理耗时长的部署请求
        'accesslog': '-',
        'errorlog': '-',
        'preload_app': True, # 预加载应用以提高性能
    }

    print(f"🚀 RWA-HUB 启动 Gunicorn，Workers: {workers}, 端口: {port}")
    print(f"💾 数据库类型: PostgreSQL - {flask_app.config.get('SQLALCHEMY_DATABASE_URI')}")
    StandaloneApplication(flask_app, options).run()

if __name__ == '__main__':
    main()