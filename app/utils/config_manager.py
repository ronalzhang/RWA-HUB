"""
配置管理工具 - 统一管理所有系统配置
"""
from app.models.admin import SystemConfig
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """统一的配置管理器"""
    
    # 固定的区块链配置（不应该修改的）
    FIXED_CONFIGS = {
        'SOLANA_USDC_MINT': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # Solana USDC官方mint地址
        'SOLANA_RPC_URL': 'https://api.mainnet-beta.solana.com',  # 默认RPC节点
    }
    
    # 默认配置值
    DEFAULT_CONFIGS = {
        'PLATFORM_FEE_ADDRESS': 'H6FMXx3s1kq1aMkYHiexVzircV31WnWaP5MSQQwfHfeW',
        'ASSET_CREATION_FEE_ADDRESS': 'H6FMXx3s1kq1aMkYHiexVzircV31WnWaP5MSQQwfHfeW',
        'ASSET_CREATION_FEE_AMOUNT': '0.02',
    }
    
    @staticmethod
    def get_config(key, default=None):
        """
        获取配置值，优先级：数据库 > 默认值 > 传入的default
        """
        try:
            # 如果是固定配置，直接返回
            if key in ConfigManager.FIXED_CONFIGS:
                return ConfigManager.FIXED_CONFIGS[key]
            
            # 仅当应用上下文存在时才查询数据库
            if current_app:
                value = SystemConfig.get_value(key)
                if value is not None:
                    return value
            
            # 使用默认配置
            if key in ConfigManager.DEFAULT_CONFIGS:
                return ConfigManager.DEFAULT_CONFIGS[key]
            
            # 使用传入的默认值
            return default
            
        except Exception as e:
            logger.error(f"获取配置 {key} 失败: {e}")
            # 发生错误时使用默认配置或传入的默认值
            return ConfigManager.DEFAULT_CONFIGS.get(key, default)
    
    @staticmethod
    def get_platform_fee_address():
        """获取平台收款地址"""
        return ConfigManager.get_config('PLATFORM_FEE_ADDRESS')
    
    @staticmethod
    def get_asset_creation_fee_address():
        """获取资产创建收款地址"""
        return ConfigManager.get_config('ASSET_CREATION_FEE_ADDRESS')
    
    @staticmethod
    def get_asset_creation_fee_amount():
        """获取资产创建费用"""
        return float(ConfigManager.get_config('ASSET_CREATION_FEE_AMOUNT', '0.02'))
    
    @staticmethod
    def get_usdc_mint():
        """获取USDC mint地址（固定值）"""
        return ConfigManager.FIXED_CONFIGS['SOLANA_USDC_MINT']
    
    @staticmethod
    def get_solana_rpc_url():
        """获取Solana RPC URL"""
        return ConfigManager.get_config('SOLANA_RPC_URL', ConfigManager.FIXED_CONFIGS['SOLANA_RPC_URL'])
    
    @staticmethod
    def get_payment_settings():
        """获取完整的支付设置"""
        from app.models.admin import SystemConfig

        # 获取平台抽佣率（20%）
        platform_commission_rate = SystemConfig.get_value('PLATFORM_COMMISSION_RATE') or 0.2

        return {
            'platform_fee_address': ConfigManager.get_platform_fee_address(),
            'asset_creation_fee_address': ConfigManager.get_asset_creation_fee_address(),
            'usdc_mint': ConfigManager.get_usdc_mint(),
            'creation_fee': {
                'amount': str(ConfigManager.get_asset_creation_fee_amount()),
                'token': 'USDC'
            },
            'platform_commission_rate': float(platform_commission_rate),
            'platform_commission_percent': float(platform_commission_rate) * 100,
            'currency': 'USDC'
        } 