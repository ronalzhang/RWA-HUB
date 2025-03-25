"""
Solana交易选项模块
提供交易创建和发送时使用的选项类
"""

from typing import Optional, Dict, List, Any


class TxOpts:
    """
    Solana交易选项类
    
    用于指定交易的预算、费用相关选项，以及其他交易设置
    """
    
    def __init__(
        self,
        skip_preflight: bool = False,
        preflight_commitment: str = "processed",
        max_retries: int = 3,
        skip_confirmation: bool = False,
        confirmation_commitment: Optional[str] = None,
        timeout: float = 30.0,
        fee_payer: Optional[str] = None,
    ):
        """
        初始化交易选项
        
        Args:
            skip_preflight: 是否跳过预检
            preflight_commitment: 预检使用的提交级别
            max_retries: 最大重试次数
            skip_confirmation: 是否跳过确认
            confirmation_commitment: 确认使用的提交级别
            timeout: 超时时间（秒）
            fee_payer: 费用支付账户
        """
        self.skip_preflight = skip_preflight
        self.preflight_commitment = preflight_commitment
        self.max_retries = max_retries
        self.skip_confirmation = skip_confirmation
        self.confirmation_commitment = confirmation_commitment
        self.timeout = timeout
        self.fee_payer = fee_payer
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将选项转换为字典格式
        
        Returns:
            Dict[str, Any]: 选项字典
        """
        result = {
            "skipPreflight": self.skip_preflight,
            "preflightCommitment": self.preflight_commitment,
            "maxRetries": self.max_retries,
        }
        
        if self.skip_confirmation:
            result["skipConfirmation"] = True
            
        if self.confirmation_commitment:
            result["confirmationCommitment"] = self.confirmation_commitment
            
        if self.timeout:
            result["timeout"] = self.timeout
            
        if self.fee_payer:
            result["feePayer"] = self.fee_payer
            
        return result
        
    @classmethod
    def default(cls) -> 'TxOpts':
        """
        获取默认交易选项
        
        Returns:
            TxOpts: 默认选项实例
        """
        return cls() 