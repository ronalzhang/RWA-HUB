"""
Solana配置验证服务
提供Solana相关配置参数的验证和检查功能
"""

import logging
import base58
from typing import Dict, List, Optional, Tuple
from flask import current_app

logger = logging.getLogger(__name__)

class SolanaConfigValidator:
    """Solana配置验证器"""
    
    REQUIRED_PARAMS = [
        'SOLANA_RPC_URL',
        'PLATFORM_TREASURY_WALLET', 
        'PAYMENT_TOKEN_MINT_ADDRESS',
        'PAYMENT_TOKEN_DECIMALS',
        'SOLANA_PROGRAM_ID'
    ]
    
    @staticmethod
    def validate_wallet_address(address: str) -> bool:
        """验证Solana钱包地址格式"""
        if not isinstance(address, str):
            return False
        try:
            # Solana地址是32字节的base58编码字符串
            decoded = base58.b58decode(address)
            return len(decoded) == 32
        except (ValueError, Exception):
            return False
    
    @staticmethod
    def validate_token_mint_address(address: str) -> bool:
        """验证代币铸造地址格式"""
        # 代币铸造地址与钱包地址格式相同
        return SolanaConfigValidator.validate_wallet_address(address)
    
    @staticmethod
    def validate_rpc_url(url: str) -> bool:
        """验证RPC URL格式"""
        if not isinstance(url, str):
            return False
        return url.startswith(('http://', 'https://')) and len(url) > 10
    
    @staticmethod
    def validate_decimals(decimals: str) -> Tuple[bool, Optional[int]]:
        """验证代币小数位数"""
        try:
            decimal_value = int(decimals)
            # USDC和大多数代币的小数位数在0-18之间
            if 0 <= decimal_value <= 18:
                return True, decimal_value
            return False, None
        except (ValueError, TypeError):
            return False, None
    
    @classmethod
    def validate_configuration(cls, app) -> Dict:
        """验证所有必需的Solana配置参数"""
        missing_params = []
        invalid_params = []
        warnings = []
        
        # 检查必需参数是否存在
        config_values = {}
        for param in cls.REQUIRED_PARAMS:
            value = app.config.get(param)
            config_values[param] = value
            
            if not value:
                missing_params.append(param)
                continue
            
            # 验证参数格式
            if param == 'SOLANA_RPC_URL':
                if not cls.validate_rpc_url(value):
                    invalid_params.append(f"{param}: 无效的RPC URL格式")
            
            elif param == 'PLATFORM_TREASURY_WALLET':
                if not cls.validate_wallet_address(value):
                    invalid_params.append(f"{param}: 无效的钱包地址格式")
            
            elif param == 'PAYMENT_TOKEN_MINT_ADDRESS':
                if not cls.validate_token_mint_address(value):
                    invalid_params.append(f"{param}: 无效的代币铸造地址格式")
            
            elif param == 'PAYMENT_TOKEN_DECIMALS':
                is_valid, decimal_value = cls.validate_decimals(str(value))
                if not is_valid:
                    invalid_params.append(f"{param}: 必须是0-18之间的整数")
                elif decimal_value != 6:
                    warnings.append(f"{param}: 当前值为{decimal_value}，USDC标准为6")
            
            elif param == 'SOLANA_PROGRAM_ID':
                if not cls.validate_wallet_address(value):
                    invalid_params.append(f"{param}: 无效的程序ID格式")
        
        # 构建验证结果
        is_valid = len(missing_params) == 0 and len(invalid_params) == 0
        
        result = {
            'valid': is_valid,
            'missing_params': missing_params,
            'invalid_params': invalid_params,
            'warnings': warnings,
            'config_values': config_values
        }
        
        if is_valid:
            result['message'] = '所有Solana配置参数验证通过'
            if warnings:
                result['message'] += f'，但有{len(warnings)}个警告'
        else:
            error_parts = []
            if missing_params:
                error_parts.append(f"缺失{len(missing_params)}个参数")
            if invalid_params:
                error_parts.append(f"有{len(invalid_params)}个参数格式无效")
            result['message'] = f"配置验证失败: {', '.join(error_parts)}"
        
        return result
    
    @classmethod
    def get_configuration_status(cls, app) -> Dict:
        """获取配置状态，包含详细信息用于调试"""
        validation_result = cls.validate_configuration(app)
        
        status = {
            'timestamp': None,  # 可以添加时间戳
            'status': 'valid' if validation_result['valid'] else 'invalid',
            'summary': validation_result['message'],
            'details': {
                'missing_parameters': validation_result['missing_params'],
                'invalid_parameters': validation_result['invalid_params'],
                'warnings': validation_result['warnings']
            },
            'configuration': validation_result['config_values']
        }
        
        return status
    
    @classmethod
    def log_configuration_status(cls, app) -> None:
        """记录配置状态到日志"""
        status = cls.get_configuration_status(app)
        
        if status['status'] == 'valid':
            logger.info(f"Solana配置验证: {status['summary']}")
            if status['details']['warnings']:
                for warning in status['details']['warnings']:
                    logger.warning(f"Solana配置警告: {warning}")
        else:
            logger.error(f"Solana配置验证失败: {status['summary']}")
            
            for param in status['details']['missing_parameters']:
                logger.error(f"缺失配置参数: {param}")
            
            for param in status['details']['invalid_parameters']:
                logger.error(f"无效配置参数: {param}")
    
    @classmethod
    def raise_for_invalid_config(cls, app) -> None:
        """如果配置无效则抛出异常"""
        validation_result = cls.validate_configuration(app)
        
        if not validation_result['valid']:
            error_details = []
            
            if validation_result['missing_params']:
                error_details.append(f"缺失参数: {', '.join(validation_result['missing_params'])}")
            
            if validation_result['invalid_params']:
                error_details.append(f"无效参数: {', '.join(validation_result['invalid_params'])}")
            
            raise ValueError(f"Solana配置验证失败: {'; '.join(error_details)}")