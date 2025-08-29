import os
from datetime import timedelta
from dotenv import load_dotenv

# 尝试加载.env文件
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"已加载环境变量文件: {dotenv_path}")
else:
    print(f"未找到环境变量文件: {dotenv_path}")

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    PURCHASE_CONTRACT_ADDRESS = os.environ.get('PURCHASE_CONTRACT_ADDRESS', 'rwaHubTradeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://rwa_hub_user:password@localhost/rwa_hub')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static/uploads')

    # Babel 配置
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_DEFAULT_TIMEZONE = 'UTC'
    LANGUAGES = ['en', 'zh_Hant']
    
    # 管理员配置
    ADMIN_CONFIG = {
        '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b': {
            'role': 'super_admin',
            'name': 'SOL超级管理员',
            'level': 1,
            'permissions': ['审核', '编辑', '删除', '发布公告', '管理用户', '查看统计']
        }
    }
    
    # 写入ADMIN_ADDRESSES以向后兼容旧代码
    ADMIN_ADDRESSES = list(ADMIN_CONFIG.keys())
    
    # 权限等级说明
    PERMISSION_LEVELS = {
        '审核': 2,    # 副管理员及以上可审核
        '编辑': 2,    # 副管理员及以上可编辑
        '删除': 1,    # 仅主管理员可删除
        '发布公告': 1,  # 仅主管理员可发布公告
        '管理用户': 1,  # 仅主管理员可管理用户
        '查看统计': 2   # 副管理员及以上可查看统计
    }
    
    class CALCULATION:
        TOKENS_PER_SQUARE_METER = 10000  # 每平方米对应的代币数量
        PRICE_DECIMALS = 6  # 代币价格小数位数
        VALUE_DECIMALS = 2  # 价值小数位数

    # 区块链网络配置
    SOLANA_RPC_URL = os.environ.get('SOLANA_RPC_URL', 'https://mainnet.helius-rpc.com/?api-key=edbb3e74-772d-4c65-a430-5c89f7ad02ea')
    SOLANA_PROGRAM_ID = os.environ.get('SOLANA_PROGRAM_ID', '2TsURTNQXyqHLB2bfbzFME7HkSMLWueYPjqXBBy2u1wP')
    SOLANA_USDC_MINT = os.environ.get('SOLANA_USDC_MINT', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')  # Mainnet USDC
    
    # Solana交易参数配置
    PLATFORM_TREASURY_WALLET = os.environ.get('PLATFORM_TREASURY_WALLET', '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b')
    PAYMENT_TOKEN_MINT_ADDRESS = os.environ.get('PAYMENT_TOKEN_MINT_ADDRESS', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')  # USDC mint address
    PAYMENT_TOKEN_DECIMALS = int(os.environ.get('PAYMENT_TOKEN_DECIMALS', 6))  # USDC has 6 decimals
    
    # 平台费用地址现在通过ConfigManager动态获取，不再使用硬编码
    # PLATFORM_FEE_ADDRESS = os.environ.get('PLATFORM_FEE_ADDRESS', '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b')
    PLATFORM_FEE_ADDRESS = os.environ.get('PLATFORM_FEE_ADDRESS', '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b')
    PLATFORM_FEE_RATE = float(os.environ.get('PLATFORM_FEE_RATE', 0.035))  # 3.5%平台费率
    PLATFORM_FEE_BASIS_POINTS = int(os.environ.get('PLATFORM_FEE_BASIS_POINTS', 350))  # 3.5%平台费率，以基点表示
    
    # 智能合约ID - 生产环境
    RWA_TRADE_PROGRAM_ID = os.environ.get('RWA_TRADE_PROGRAM_ID', '2TsURTNQXyqHLB2bfbzFME7HkSMLWueYPjqXBBy2u1wP')
    RWA_DIVIDEND_PROGRAM_ID = os.environ.get('RWA_DIVIDEND_PROGRAM_ID', '2TsURTNQXyqHLB2bfbzFME7HkSMLWueYPjqXBBy2u1wP')
    
    ETH_RPC_URL = os.environ.get('ETH_RPC_URL', 'https://rpc.ankr.com/eth')
    ETH_USDC_CONTRACT = os.environ.get('ETH_USDC_CONTRACT', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
    
    # Redis缓存配置
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 300  # 5分钟默认缓存时间
    
    # 性能优化配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'max_overflow': 30,
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }

    @staticmethod
    def validate_solana_configuration(app):
        """验证所有必需的Solana配置参数 - 使用SolanaConfigValidator"""
        # Import here to avoid circular imports
        from app.services.solana_config_validator import SolanaConfigValidator
        
        result = SolanaConfigValidator.validate_configuration(app)
        
        if not result['valid']:
            error_parts = []
            if result['missing_params']:
                error_parts.append(f"缺失参数: {', '.join(result['missing_params'])}")
            if result['invalid_params']:
                error_parts.append(f"无效参数: {', '.join(result['invalid_params'])}")
            raise ValueError(f"Solana配置验证失败: {'; '.join(error_parts)}")
        
        return True
    
    @staticmethod
    def get_solana_config_status():
        """获取Solana配置状态，用于调试和监控 - 使用SolanaConfigValidator"""
        try:
            from app.services.solana_config_validator import SolanaConfigValidator
            from flask import current_app
            
            # Try to use the validator if in app context
            return SolanaConfigValidator.get_configuration_status()
        except (RuntimeError, ImportError):
            # Fallback to basic status check
            try:
                Config.validate_solana_configuration()
                return {
                    'status': 'valid',
                    'message': '所有Solana配置参数已正确设置',
                    'config': {
                        'SOLANA_RPC_URL': os.environ.get('SOLANA_RPC_URL', 'NOT_SET'),
                        'PLATFORM_TREASURY_WALLET': os.environ.get('PLATFORM_TREASURY_WALLET', 'NOT_SET'),
                        'PAYMENT_TOKEN_MINT_ADDRESS': os.environ.get('PAYMENT_TOKEN_MINT_ADDRESS', 'NOT_SET'),
                        'PAYMENT_TOKEN_DECIMALS': os.environ.get('PAYMENT_TOKEN_DECIMALS', 'NOT_SET'),
                        'SOLANA_PROGRAM_ID': os.environ.get('SOLANA_PROGRAM_ID', 'NOT_SET')
                    }
                }
            except ValueError as e:
                return {
                    'status': 'invalid',
                    'message': str(e),
                    'config': {
                        'SOLANA_RPC_URL': os.environ.get('SOLANA_RPC_URL', 'NOT_SET'),
                        'PLATFORM_TREASURY_WALLET': os.environ.get('PLATFORM_TREASURY_WALLET', 'NOT_SET'),
                        'PAYMENT_TOKEN_MINT_ADDRESS': os.environ.get('PAYMENT_TOKEN_MINT_ADDRESS', 'NOT_SET'),
                        'PAYMENT_TOKEN_DECIMALS': os.environ.get('PAYMENT_TOKEN_DECIMALS', 'NOT_SET'),
                        'SOLANA_PROGRAM_ID': os.environ.get('SOLANA_PROGRAM_ID', 'NOT_SET')
                    }
                }

    @staticmethod
    def init_app(app):
        # 基础配置初始化
        from app.services.database_optimizer import get_database_optimizer
        from app.services.cache_service import get_cache_manager
        
        # 验证Solana配置
        try:
            Config.validate_solana_configuration(app)
            print("✓ Solana配置验证通过")
            
            # 使用SolanaConfigValidator进行详细日志记录
            try:
                from app.services.solana_config_validator import SolanaConfigValidator
                SolanaConfigValidator.log_configuration_status(app)
            except ImportError:
                pass  # 如果导入失败，继续使用基本验证
                
        except ValueError as e:
            print(f"⚠ Solana配置验证失败: {e}")
            # 在开发环境中，我们可以继续运行，但会记录警告
            # 在生产环境中，可能需要停止应用启动
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Solana配置验证失败，但应用将继续启动: {e}")
            logger.warning("请检查环境变量或配置文件中的Solana相关参数")
            
            # 尝试使用SolanaConfigValidator记录详细错误
            try:
                from app.services.solana_config_validator import SolanaConfigValidator
                SolanaConfigValidator.log_configuration_status(app)
            except ImportError:
                pass
        
        # 初始化数据库优化
        db_optimizer = get_database_optimizer()
        db_optimizer.optimize_connection_pool(app)
        
        # 初始化缓存
        cache_manager = get_cache_manager()
        
        # 在应用启动后创建索引（延迟执行）

class DevelopmentConfig(Config):
    DEBUG = True
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        # 开发环境特定的配置
        pass

class ProductionConfig(Config):
    DEBUG = False
    
    # 生产环境数据库配置 - 本地开发环境不需要SSL
    SQLALCHEMY_DATABASE_URI = 'postgresql://rwa_hub_user:password@localhost/rwa_hub'
    print(f"生产环境使用本地数据库: {SQLALCHEMY_DATABASE_URI}")
    
    # 明确从环境变量获取SOLANA_RPC_URL
    SOLANA_RPC_URL = os.environ.get('SOLANA_RPC_URL', 'https://mainnet.helius-rpc.com/?api-key=edbb3e74-772d-4c65-a430-5c89f7ad02ea')
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        # 生产环境特定的配置
        pass

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}