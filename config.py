import os

# Solana网络配置
SOLANA_ENDPOINT = os.environ.get('SOLANA_ENDPOINT', 'https://api.mainnet-beta.solana.com')

# Solana程序ID (替换为您的实际部署ID)
SOLANA_PROGRAM_ID = os.environ.get('SOLANA_PROGRAM_ID', 'rwaHubTradeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX') # 示例ID，请替换

# 新增：平台手续费基点 (例如 100 代表 1%)
PLATFORM_FEE_BASIS_POINTS = int(os.environ.get('PLATFORM_FEE_BASIS_POINTS', '150'))

# 购买合约地址
PURCHASE_CONTRACT_ADDRESS = os.environ.get('PURCHASE_CONTRACT_ADDRESS', 'rwaHubTradeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')

# 平台手续费收款地址
    # 平台费用地址现在通过ConfigManager动态获取，不再使用硬编码
    # PLATFORM_FEE_ADDRESS = os.environ.get('PLATFORM_FEE_ADDRESS', 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4')

# USDC代币地址
USDC_TOKEN_ADDRESS = os.environ.get('USDC_TOKEN_ADDRESS', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')

# 其他配置...
# 如果有其他配置类，请确保添加到合适的类中或保持在全局 

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret-key-needs-to-be-changed'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 最大上传文件大小: 20MB
    
    # Solana配置
    SOLANA_RPC_URL = os.environ.get('SOLANA_RPC_URL') or 'https://api.mainnet-beta.solana.com'
    SOLANA_ENDPOINT = os.environ.get('SOLANA_ENDPOINT') or 'https://api.mainnet-beta.solana.com'
    SOLANA_PROGRAM_ID = os.environ.get('SOLANA_PROGRAM_ID') or 'RWAxxx111111111111111111111111111111111111'
    SOLANA_USDC_MINT = os.environ.get('SOLANA_USDC_MINT') or 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
    SOLANA_USDC_DECIMALS = 6 