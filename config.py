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
PLATFORM_FEE_ADDRESS = os.environ.get('PLATFORM_FEE_ADDRESS', 'HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd')

# USDC代币地址
USDC_TOKEN_ADDRESS = os.environ.get('USDC_TOKEN_ADDRESS', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')

# 其他配置...
# 如果有其他配置类，请确保添加到合适的类中或保持在全局 