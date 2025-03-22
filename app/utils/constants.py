"""
应用常量定义
"""

# 区块链相关常量
MIN_SOL_BALANCE = 0.1  # 服务钱包最低SOL余额
MIN_ETH_BALANCE = 0.01  # 服务钱包最低ETH余额
MIN_USDC_BALANCE = 10   # 服务钱包最低USDC余额

# 平台费率常量
PLATFORM_FEE_RATE = 0.02  # 平台收取2%的费用
REFERRAL_COMMISSION_RATE = 0.01  # 推荐人获得1%的佣金

# 页面相关常量
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# 资产相关常量
MAX_ASSET_DESCRIPTION_LENGTH = 5000  # 资产描述最大长度
MAX_ASSET_NAME_LENGTH = 100  # 资产名称最大长度
MAX_ASSET_IMAGES = 10  # 资产图片最大数量

# 用户相关常量
MAX_LOGIN_ATTEMPTS = 5  # 最大登录尝试次数
LOGIN_COOLDOWN_MINUTES = 15  # 登录冷却时间（分钟）
SESSION_TIMEOUT_MINUTES = 60  # 会话超时时间（分钟）
PASSWORD_MIN_LENGTH = 8  # 密码最小长度 