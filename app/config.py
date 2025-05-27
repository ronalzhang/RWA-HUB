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
        'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4': {
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
    SOLANA_RPC_URL = os.environ.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
    SOLANA_PROGRAM_ID = os.environ.get('SOLANA_PROGRAM_ID', '2TsURTNQXyqHLB2bfbzFME7HkSMLWueYPjqXBBy2u1wP')
    SOLANA_USDC_MINT = os.environ.get('SOLANA_USDC_MINT', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')  # Mainnet USDC
    # 平台费用地址现在通过ConfigManager动态获取，不再使用硬编码
    # PLATFORM_FEE_ADDRESS = os.environ.get('PLATFORM_FEE_ADDRESS', 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4')
    PLATFORM_FEE_RATE = float(os.environ.get('PLATFORM_FEE_RATE', 0.035))  # 3.5%平台费率
    PLATFORM_FEE_BASIS_POINTS = int(os.environ.get('PLATFORM_FEE_BASIS_POINTS', 350))  # 3.5%平台费率，以基点表示
    
    # 智能合约ID - 生产环境
    RWA_TRADE_PROGRAM_ID = os.environ.get('RWA_TRADE_PROGRAM_ID', '2TsURTNQXyqHLB2bfbzFME7HkSMLWueYPjqXBBy2u1wP')
    RWA_DIVIDEND_PROGRAM_ID = os.environ.get('RWA_DIVIDEND_PROGRAM_ID', '2TsURTNQXyqHLB2bfbzFME7HkSMLWueYPjqXBBy2u1wP')
    
    ETH_RPC_URL = os.environ.get('ETH_RPC_URL', 'https://rpc.ankr.com/eth')
    ETH_USDC_CONTRACT = os.environ.get('ETH_USDC_CONTRACT', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')

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
    
    # !! 关键改动：直接指定生产环境使用本地数据库 !!
    SQLALCHEMY_DATABASE_URI = 'postgresql://rwa_hub_user:password@localhost/rwa_hub?sslmode=disable'
    print(f"生产环境强制使用本地数据库 (SSL disabled): {SQLALCHEMY_DATABASE_URI}")
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        # 生产环境特定的配置 (数据库URI已在类级别硬编码为本地)
        pass

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
