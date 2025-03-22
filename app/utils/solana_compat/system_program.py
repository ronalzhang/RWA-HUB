from typing import List, Union, Optional
from .publickey import PublicKey
from .transaction import TransactionInstruction, AccountMeta
import struct

class SystemProgram:
    """System program 接口"""
    
    # 系统程序ID
    PROGRAM_ID = PublicKey("11111111111111111111111111111111")
    
    @staticmethod
    def create_account(
        from_pubkey: PublicKey,
        new_account_pubkey: PublicKey,
        lamports: int,
        space: int,
        program_id: PublicKey
    ) -> TransactionInstruction:
        """创建一个新账户的指令"""
        data = struct.pack("<IQQ32s", 0, lamports, space, bytes(program_id._key))
        
        keys = [
            AccountMeta(from_pubkey, True, True),
            AccountMeta(new_account_pubkey, True, True),
        ]
        
        return TransactionInstruction(
            keys=keys,
            program_id=SystemProgram.PROGRAM_ID,
            data=data
        )
    
    @staticmethod
    def transfer(
        from_pubkey: PublicKey,
        to_pubkey: PublicKey,
        lamports: int
    ) -> TransactionInstruction:
        """创建一个转账指令"""
        data = struct.pack("<IQ", 2, lamports)
        
        keys = [
            AccountMeta(from_pubkey, True, True),
            AccountMeta(to_pubkey, False, True),
        ]
        
        return TransactionInstruction(
            keys=keys,
            program_id=SystemProgram.PROGRAM_ID,
            data=data
        )
    
    @staticmethod
    def assign(
        account_pubkey: PublicKey,
        program_id: PublicKey
    ) -> TransactionInstruction:
        """创建分配指令"""
        data = struct.pack("<I32s", 1, bytes(program_id._key))
        
        return TransactionInstruction(
            keys=[AccountMeta(account_pubkey, True, True)],
            program_id=SystemProgram.PROGRAM_ID,
            data=data
        ) 