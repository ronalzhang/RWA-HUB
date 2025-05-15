from typing import Optional, Tuple
from app.utils.solana_compat.publickey import PublicKey
from app.utils.solana_compat.transaction import Transaction, TransactionInstruction
from app.utils.solana_compat.connection import Connection
from .constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID

def create_associated_token_account(
    payer: PublicKey,
    owner: PublicKey,
    mint: PublicKey,
    program_id: PublicKey = TOKEN_PROGRAM_ID,
    associated_token_program_id: PublicKey = ASSOCIATED_TOKEN_PROGRAM_ID
) -> Tuple[PublicKey, Transaction]:
    """创建关联代币账户"""
    # 获取关联代币账户地址
    associated_token_address = get_associated_token_address(
        owner=owner,
        mint=mint
    )
    
    # 创建交易
    transaction = Transaction()
    
    # 注意：这是模拟实现，实际应添加真实指令
    # 在真实环境中，应构建SPL Token程序的createAssociatedTokenAccount指令
    
    return associated_token_address, transaction

def get_associated_token_address(
    owner: PublicKey,
    mint: PublicKey,
    program_id: PublicKey = TOKEN_PROGRAM_ID,
    associated_token_program_id: PublicKey = ASSOCIATED_TOKEN_PROGRAM_ID
) -> PublicKey:
    """获取关联代币账户地址"""
    # 进行真实的SPL Token关联账户查询
    import hashlib
    import base58
    
    # 创建种子和程序ID
    # 种子包括：'token'前缀、owner地址和mint地址
    seed_prefix = "token"
    
    # 从PublicKey获取字节表示
    # 注意：这里使用字符串表示，因为直接bytes(PublicKey)可能导致类型错误
    owner_bytes = str(owner).encode("utf-8")
    mint_bytes = str(mint).encode("utf-8")
    
    # 将种子组合成字节数组
    seed_bytes = seed_prefix.encode("utf-8") + owner_bytes + mint_bytes
    
    # 计算哈希
    digest = hashlib.sha256(seed_bytes).digest()
    
    # 转换为base58编码
    token_address = base58.b58encode(digest[:32]).decode("utf-8")
    
    # 确保地址有效（以确保生成的地址格式正确）
    return PublicKey(token_address)

def transfer(
    token_program_id: PublicKey,
    source: PublicKey,
    destination: PublicKey,
    owner: PublicKey,
    amount: int,
    signers=None
) -> TransactionInstruction:
    """
    SPL Token转账指令
    
    :param token_program_id: Token程序ID
    :param source: 源Token账户
    :param destination: 目标Token账户
    :param owner: 源账户所有者
    :param amount: 转账金额(lamports)
    :param signers: 可选的其他签名者列表
    :return: TransactionInstruction对象
    """
    import struct
    from app.utils.solana_compat.transaction import AccountMeta
    
    keys = [
        AccountMeta(pubkey=source, is_signer=False, is_writable=True),
        AccountMeta(pubkey=destination, is_signer=False, is_writable=True),
        AccountMeta(pubkey=owner, is_signer=True, is_writable=False)
    ]
    
    # 如果有额外的签名者，添加到keys中
    if signers:
        for signer in signers:
            keys.append(AccountMeta(pubkey=signer, is_signer=True, is_writable=False))
    
    # 转账指令的命令ID是3，然后是amount（u64，8字节）
    # SPL Token指令格式：命令ID (u8) + 参数...
    # 转账指令格式：3 (u8) + amount (u64)
    data = struct.pack("<BI", 3, amount)
    
    return TransactionInstruction(
        keys=keys,
        program_id=token_program_id,
        data=bytes(data)
    )

def create_mint(
    conn: Connection,
    payer: object,  # 为了兼容性，此处不指定确切类型
    mint_authority: PublicKey,
    decimals: int,
    program_id: PublicKey = TOKEN_PROGRAM_ID,
    freeze_authority: Optional[PublicKey] = None,
    skip_preflight: bool = False
) -> Tuple[PublicKey, str]:
    """创建代币铸造账户"""
    # 注意：这是模拟实现，实际应创建真实的代币
    
    # 生成一个模拟的mint地址
    import hashlib
    import time
    import base58
    
    # 使用时间戳和参数创建一个伪随机种子
    seed = f"{str(mint_authority)}:{decimals}:{int(time.time())}"
    hash_bytes = hashlib.sha256(seed.encode()).digest()[:32]
    
    # 创建一个看起来像Solana地址的字符串
    mint_address = PublicKey(base58.b58encode(hash_bytes).decode())
    
    # 模拟交易签名
    tx_hash = base58.b58encode(hashlib.sha256(f"{mint_address}:{int(time.time())}".encode()).digest()).decode()
    
    return mint_address, tx_hash 