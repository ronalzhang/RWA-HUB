import sys
import os
import logging
logger = logging.getLogger(__name__)
logger.critical("!!! GEMINI DEBUG START !!!")
logger.critical(f"Python Executable: {sys.executable}")
logger.critical(f"sys.path: {sys.path}")
logger.critical(f"Current Working Directory: {os.getcwd()}")
logger.critical(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
logger.critical("!!! GEMINI DEBUG END !!!")

import logging
import os
import sys
import traceback
from app import create_app

# 配置日志
logging.basicConfig(level=logging.INFO)

# 创建应用实例，供Gunicorn等WSGI服务器使用
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

def load_encrypted_config(app_context):
    """启动时加载加密的配置"""
    with app_context:
        try:
            from app.models.admin import SystemConfig
            from app.utils.crypto_manager import get_crypto_manager
            
            # 获取加密的私钥和密码
            encrypted_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY_ENCRYPTED')
            encrypted_password = SystemConfig.get_value('CRYPTO_PASSWORD_ENCRYPTED')
            
            if encrypted_key and encrypted_password:
                # 解密用户密码
                original_password = os.environ.get('CRYPTO_PASSWORD')
                os.environ['CRYPTO_PASSWORD'] = 'RWA_HUB_SYSTEM_KEY_2024'
                
                try:
                    system_crypto = get_crypto_manager()
                    crypto_password = system_crypto.decrypt_private_key(encrypted_password)
                    
                    # 设置环境变量
                    os.environ['CRYPTO_PASSWORD'] = crypto_password
                    os.environ['SOLANA_PRIVATE_KEY_ENCRYPTED'] = encrypted_key
                    
                    app.logger.info("✅ 成功加载加密的私钥配置")
                    
                except Exception as e:
                    app.logger.error(f"❌ 加载加密配置失败: {e}")
                    if original_password:
                        os.environ['CRYPTO_PASSWORD'] = original_password
            else:
                app.logger.info("ℹ️  未找到加密的私钥配置，将使用环境变量中的配置")
                
        except Exception as e:
            app.logger.error(f"❌ 加载加密配置时出错: {e}")

if __name__ == '__main__':
    # 确保应用配置使用正确的数据库URI
    with app.app_context():
        db_uri = os.environ.get('DATABASE_URL', 'postgresql://rwa_hub_user:password@localhost/rwa_hub')
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # 加载加密配置
        load_encrypted_config(app.app_context())
    
    # RWA-HUB 使用默认端口 9000
    logger = app.logger
    port = int(os.environ.get('PORT', 9000))
    logger.info(f"🚀 RWA-HUB 启动应用，访问地址: http://localhost:{port}")
    logger.info(f"📱 v6版本界面地址: http://localhost:{port}/v6")
    logger.info(f"💾 数据库类型: PostgreSQL - {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    try:
        app.run(host='0.0.0.0', port=port, debug=False)  # 生产环境关闭debug模式
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        traceback.print_exc()
        sys.exit(1)