# Solana程序ID (替换为您的实际部署ID)
SOLANA_PROGRAM_ID = os.environ.get('SOLANA_PROGRAM_ID', 'rwaHubTradeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX') # 示例ID，请替换

# 新增：平台手续费基点 (例如 100 代表 1%)
PLATFORM_FEE_BASIS_POINTS = int(os.environ.get('PLATFORM_FEE_BASIS_POINTS', '100'))

# 其他配置...
# 如果有其他配置类，请确保添加到合适的类中或保持在全局 