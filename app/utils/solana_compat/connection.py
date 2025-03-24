from typing import Dict, Any, Optional, List, Union, Callable
from .rpc.api import Client
from .rpc.types import TxOpts
from .publickey import PublicKey
from .transaction import Transaction

class Connection:
    """连接到Solana集群的连接类"""
    
    def __init__(self, endpoint: str, commitment: Optional[str] = "confirmed"):
        """初始化连接"""
        self.commitment = commitment
        self.rpc_client = Client(endpoint)
    
    def get_account_info(
        self, public_key: Union[PublicKey, str], commitment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取账户信息
        
        Args:
            public_key: 要获取信息的账户公钥
            commitment: 可选的承诺级别
            
        Returns:
            Dict包含账户信息
        """
        pubkey_str = str(public_key) if isinstance(public_key, PublicKey) else public_key
        return self.rpc_client.get_account_info(pubkey_str, commitment or self.commitment)
    
    def get_balance(
        self, public_key: Union[PublicKey, str], commitment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取账户余额
        
        Args:
            public_key: 要获取余额的账户公钥
            commitment: 可选的承诺级别
            
        Returns:
            Dict包含余额信息
        """
        pubkey_str = str(public_key) if isinstance(public_key, PublicKey) else public_key
        return self.rpc_client.get_balance(pubkey_str, commitment or self.commitment)
    
    def get_recent_blockhash(self, commitment: Optional[str] = None) -> Dict[str, Any]:
        """
        获取最近的区块哈希
        
        Args:
            commitment: 可选的承诺级别
            
        Returns:
            Dict包含最近的区块哈希
        """
        return self.rpc_client.get_recent_blockhash(commitment or self.commitment)
    
    def send_transaction(
        self, transaction: Transaction, signers: List[Any] = None, opts: Optional[TxOpts] = None
    ) -> Dict[str, Any]:
        """
        发送交易
        
        Args:
            transaction: 要发送的交易
            signers: 交易的签名者列表
            opts: 可选的交易选项
            
        Returns:
            Dict包含交易结果
        """
        if signers:
            transaction.sign(*signers)
        
        return self.rpc_client.send_transaction(transaction, opts)
    
    def confirm_transaction(
        self, signature: str, commitment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        确认交易
        
        Args:
            signature: 交易签名
            commitment: 可选的承诺级别
            
        Returns:
            Dict包含交易确认状态
        """
        return self.rpc_client.get_transaction(signature, commitment or self.commitment)
    
    def get_slot(self, commitment: Optional[str] = None) -> Dict[str, Any]:
        """
        获取当前slot
        
        Args:
            commitment: 可选的承诺级别
            
        Returns:
            Dict包含当前slot信息
        """
        return self.rpc_client.get_slot(commitment or self.commitment)
    
    def send_raw_transaction(
        self, raw_transaction: bytes, opts: Optional[TxOpts] = None
    ) -> str:
        """
        发送已签名的原始交易数据
        
        Args:
            raw_transaction: 已签名的交易字节数据
            opts: 可选的交易选项
            
        Returns:
            交易签名字符串
        """
        response = self.rpc_client.send_raw_transaction(raw_transaction, opts)
        if "error" in response:
            error_msg = response.get("error", {}).get("message", "Unknown error")
            raise Exception(f"发送交易失败: {error_msg}")
        
        return response.get("result", "") 