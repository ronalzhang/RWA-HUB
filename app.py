import logging
import os
from app import create_app

# 配置日志
logging.basicConfig(level=logging.DEBUG)

def load_encrypted_config():
    """启动时加载加密的配置"""
    try:
        from app.models.admin import SystemConfig
        from app.utils.crypto_manager import get_crypto_manager
        import os
        
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
                
                print(f"✅ 成功加载加密的私钥配置")
                
            except Exception as e:
                print(f"❌ 加载加密配置失败: {e}")
                if original_password:
                    os.environ['CRYPTO_PASSWORD'] = original_password
        else:
            print("ℹ️  未找到加密的私钥配置，将使用环境变量中的配置")
            
    except Exception as e:
        print(f"❌ 加载加密配置时出错: {e}")

# 修复PostgreSQL SSL配置问题 - 本地开发环境不需要SSL
if not os.environ.get('DATABASE_URL'):
    os.environ['DATABASE_URL'] = 'postgresql://rwa_hub_user:password@localhost/rwa_hub'

# 创建应用实例
app = create_app()

# 确保应用配置使用正确的数据库URI
db_uri = os.environ.get('DATABASE_URL', 'postgresql://rwa_hub_user:password@localhost/rwa_hub')
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if __name__ == '__main__':
    # 在应用上下文中加载加密配置
    with app.app_context():
        load_encrypted_config()
    
    # RWA-HUB 使用默认端口 5000
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 RWA-HUB 启动应用，访问地址: http://localhost:{port}")
    print(f"📱 v6版本界面地址: http://localhost:{port}/v6")
    print(f"💾 数据库类型: PostgreSQL - {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    app.run(host='0.0.0.0', port=port, debug=True)