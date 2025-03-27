from typing import Optional, List, Union
from ..publickey import PublicKey
from ..transaction import Transaction
from ..connection import Connection
from .constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID

def get_associated_token_address(owner: PublicKey, mint: PublicKey) -> PublicKey:
    """获取关联代币账户地址"""
    return PublicKey(str(owner)[:32])  # 模拟实现，仅用于测试

def create_associated_token_account_instruction(
    payer: PublicKey,
    owner: PublicKey,
    mint: PublicKey,
    program_id: PublicKey = TOKEN_PROGRAM_ID,
    associated_token_program_id: PublicKey = ASSOCIATED_TOKEN_PROGRAM_ID
) -> Transaction:
    """创建关联代币账户指令"""
    return Transaction()  # 模拟实现，仅用于测试

class Token:
    """SPL Token 程序接口"""
    
    def __init__(self, connection: Connection, program_id: PublicKey = TOKEN_PROGRAM_ID):
        self.connection = connection
        self.program_id = program_id
    
    def create_account(
        self,
        owner: PublicKey,
        mint: PublicKey,
        owner_authority: PublicKey,
        amount: int,
        decimals: int,
        program_id: PublicKey = TOKEN_PROGRAM_ID
    ) -> Transaction:
        """创建代币账户"""
        return Transaction()  # 模拟实现，仅用于测试
    
    def transfer(
        self,
        source: PublicKey,
        dest: PublicKey,
        owner: PublicKey,
        amount: int,
        multi_signers: Optional[List[PublicKey]] = None,
        program_id: PublicKey = TOKEN_PROGRAM_ID
    ) -> Transaction:
        """转账代币"""
        return Transaction()  # 模拟实现，仅用于测试
    
    def get_balance(self, account: PublicKey) -> int:
        """获取代币余额"""
        return 0  # 模拟实现，仅用于测试
    
    def get_accounts(
        self,
        owner: PublicKey,
        program_id: PublicKey = TOKEN_PROGRAM_ID
    ) -> List[PublicKey]:
        """获取所有代币账户"""
        return []  # 模拟实现，仅用于测试

def create_account(owner: PublicKey) -> PublicKey:
    """创建Token账户"""
    # 简化实现，返回一个固定的地址
    return PublicKey("ATokenAcc" + str(owner)[:20])

def transfer(source: PublicKey, dest: PublicKey, owner: PublicKey, amount: int) -> Transaction:
    """转移Token"""
    # 创建一个空交易，简化实现
    tx = Transaction()
    # 实际实现中应该添加转账指令
    return tx

def get_balance(account: PublicKey) -> int:
    """获取Token余额"""
    # 简化实现，返回固定值
    return 1000000

def get_accounts(owner: PublicKey) -> List[PublicKey]:
    """获取所有者的Token账户"""
    # 简化实现，返回一个固定账户
    return [get_associated_token_address(owner, TOKEN_PROGRAM_ID)] 