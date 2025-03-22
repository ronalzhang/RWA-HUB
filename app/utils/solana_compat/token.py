from typing import Optional, List, Union
from .publickey import PublicKey
from .transaction import Transaction
from .connection import Connection

# SPL Token常量
TOKEN_PROGRAM_ID = PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM_ID = PublicKey("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

class Token:
    """SPL Token程序接口"""
    
    def __init__(self, conn: Connection, pubkey: PublicKey, program_id: PublicKey, payer: Optional[PublicKey] = None):
        """初始化Token客户端"""
        self.conn = conn
        self.pubkey = pubkey
        self.program_id = program_id
        self.payer = payer
    
    def create_account(self, owner: PublicKey) -> PublicKey:
        """创建Token账户"""
        # 简化实现，返回一个固定的地址
        return PublicKey("ATokenAcc" + str(owner)[:20])
    
    def get_associated_token_address(self, owner: PublicKey) -> PublicKey:
        """获取关联Token地址"""
        # 简化实现，生成一个派生地址
        seeds = [bytes(owner), bytes(self.program_id), bytes(self.pubkey)]
        bytes_data = b"".join(seeds)
        if len(bytes_data) != 32:
            bytes_data = bytes_data[:32] if len(bytes_data) > 32 else bytes_data.ljust(32, b'\0')
        return PublicKey(bytes_data)
    
    def create_associated_token_account(self, owner: PublicKey) -> PublicKey:
        """创建关联Token账户"""
        # 简化实现，返回关联地址
        return self.get_associated_token_address(owner)
    
    def transfer(self, source: PublicKey, dest: PublicKey, owner: PublicKey, amount: int) -> Transaction:
        """转移Token"""
        # 创建一个空交易，简化实现
        tx = Transaction()
        # 实际实现中应该添加转账指令
        return tx
    
    def get_balance(self, account: PublicKey) -> int:
        """获取Token余额"""
        # 简化实现，返回固定值
        return 1000000
    
    def get_accounts(self, owner: PublicKey) -> List[PublicKey]:
        """获取所有者的Token账户"""
        # 简化实现，返回一个固定账户
        return [self.get_associated_token_address(owner)] 