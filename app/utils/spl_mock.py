"""
SPL Token模块的模拟实现，用于在无法安装原始模块的环境中提供基本功能
"""

from app.utils.solana_compat.publickey import PublicKey

# 常量定义
class Constants:
    TOKEN_PROGRAM_ID = PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
    ASSOCIATED_TOKEN_PROGRAM_ID = PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
    
# 指令函数
def get_associated_token_address(owner: PublicKey, mint: PublicKey) -> PublicKey:
    """
    计算关联代币账户地址
    """
    seeds = [
        owner.to_bytes(),
        Constants.TOKEN_PROGRAM_ID.to_bytes(),
        mint.to_bytes(),
    ]
    
    program_derived_address, nonce = PublicKey.find_program_address(
        seeds, Constants.ASSOCIATED_TOKEN_PROGRAM_ID
    )
    
    return program_derived_address 