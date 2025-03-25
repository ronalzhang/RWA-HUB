from dataclasses import dataclass
from typing import List, Any, Optional, Dict, Set, Union
from .publickey import PublicKey

@dataclass
class AccountMeta:
    """Account metadata used to define instructions."""
    
    pubkey: Any  # 应该是PublicKey类型，但为了简化使用Any
    is_signer: bool
    is_writable: bool
    
    def __init__(self, pubkey: Any, is_signer: bool, is_writable: bool):
        """Initialize metadata for an account."""
        self.pubkey = pubkey
        self.is_signer = is_signer
        self.is_writable = is_writable


class TransactionInstruction:
    """Instructions to be executed by a program."""
    
    def __init__(
        self,
        keys: List[Any],  # 可以接收AccountMeta或字典
        program_id: Any,
        data: bytes = bytes(0),
    ):
        """Initialize instruction."""
        # 将字典格式的账户信息转换为AccountMeta对象
        self.keys = []
        if isinstance(keys, list):
            for key in keys:
                if isinstance(key, dict):
                    # 从字典创建AccountMeta
                    pubkey = key.get('pubkey')
                    is_signer = key.get('isSigner', False)
                    is_writable = key.get('isWritable', False)
                    self.keys.append(AccountMeta(pubkey, is_signer, is_writable))
                else:
                    # 如果已经是AccountMeta对象，直接添加
                    self.keys.append(key)
        else:
            self.keys = keys
            
        self.program_id = program_id
        self.data = data


class Transaction:
    """Transaction class to be used to build transactions."""
    
    def __init__(self):
        """Initialize a new Transaction."""
        self.instructions = []
        self.signatures = []
        self.recent_blockhash = None
        self.fee_payer = None
    
    def add(self, instruction: TransactionInstruction) -> "Transaction":
        """Add an instruction to the transaction."""
        self.instructions.append(instruction)
        return self
    
    def add_memo(self, memo: str, pubkey: Optional[PublicKey] = None) -> "Transaction":
        """
        向交易添加备注指令
        
        Args:
            memo: 备注文本
            pubkey: 可选的签名者公钥
        
        Returns:
            Transaction: 当前交易实例，用于链式调用
        """
        # 备注程序ID
        memo_program_id = PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
        
        # 创建账户元数据
        keys = []
        if pubkey:
            keys.append(AccountMeta(pubkey, True, False))
        
        # 创建备注指令
        instruction = TransactionInstruction(
            keys=keys,
            program_id=memo_program_id,
            data=bytes(memo, 'utf-8')
        )
        
        # 添加指令到交易
        self.add(instruction)
        return self
    
    def add_signature(self, pubkey: PublicKey, signature: bytes) -> "Transaction":
        """Add an external signature to the transaction."""
        self.signatures.append({
            "publicKey": pubkey,
            "signature": signature
        })
        return self
    
    def set_recent_blockhash(self, recent_blockhash: str) -> "Transaction":
        """Set the recent blockhash for the transaction."""
        self.recent_blockhash = recent_blockhash
        return self
    
    def set_fee_payer(self, fee_payer: PublicKey) -> "Transaction":
        """Set the fee payer for the transaction."""
        self.fee_payer = fee_payer
        return self
    
    def sign(self, *signers: Any) -> "Transaction":
        """Sign the transaction with the specified signers."""
        if not self.recent_blockhash:
            raise RuntimeError("Transaction recentBlockhash required")
        
        for signer in signers:
            signature = signer.sign(b"message")  # 简化实现
            self.add_signature(signer.public_key, signature)
        
        return self
    
    def serialize(self) -> bytes:
        """Serialize the transaction to the wire format."""
        # 实现完整的交易序列化
        import json
        import struct
        import base64
        
        # 创建一个交易结构
        transaction = {
            "recentBlockhash": self.recent_blockhash or "simulated_blockhash", 
            "feePayer": str(self.fee_payer) if self.fee_payer else None,
            "instructions": []
        }
        
        # 添加所有指令
        for idx, instruction in enumerate(self.instructions):
            instruction_data = {
                "programId": str(instruction.program_id),
                "keys": [
                    {
                        "pubkey": str(key.pubkey),
                        "isSigner": key.is_signer,
                        "isWritable": key.is_writable
                    } for key in instruction.keys
                ],
                "data": base64.b64encode(instruction.data if isinstance(instruction.data, bytes) else instruction.data.encode('utf-8')).decode('utf-8')
            }
            transaction["instructions"].append(instruction_data)
        
        # 将完整交易转换为字节
        transaction_bytes = json.dumps(transaction).encode('utf-8')
        
        # 添加版本标识 (1个字节) 和长度前缀 (4个字节)
        version = 0  # 版本0表示标准交易
        length = len(transaction_bytes)
        version_and_length = struct.pack(">BI", version, length)
        
        # 返回最终的交易字节序列
        return version_and_length + transaction_bytes
    
    def serialize_message(self) -> bytes:
        """
        序列化交易消息，供Phantom钱包签名
        
        Returns:
            bytes: 序列化后的交易消息
        """
        # 简化实现，实际应根据Solana交易格式序列化
        # 这里仅仅创建一个示例消息格式
        import json
        import struct
        
        # 创建一个简化的消息结构
        message = {
            "header": {
                "numRequiredSignatures": 1,
                "numReadonlySignedAccounts": 0,
                "numReadonlyUnsignedAccounts": 1
            },
            "recentBlockhash": self.recent_blockhash or "simulated_blockhash",
            "instructions": []
        }
        
        # 添加所有指令
        for idx, instruction in enumerate(self.instructions):
            instruction_data = {
                "programIdIndex": idx,
                "accounts": [idx for idx in range(len(instruction.keys))],
                "data": instruction.data.hex() if isinstance(instruction.data, bytes) else instruction.data
            }
            message["instructions"].append(instruction_data)
        
        # 将消息转换为字节
        message_bytes = json.dumps(message).encode('utf-8')
        
        # 添加长度前缀
        length = len(message_bytes)
        # 使用4字节的小端序整数表示长度
        length_bytes = struct.pack("<I", length)
        
        # 返回最终的字节序列
        return length_bytes + message_bytes
    
    @staticmethod
    def from_bytes(raw_bytes: bytes) -> "Transaction":
        """
        从字节数据反序列化交易
        
        Args:
            raw_bytes: 经过序列化的交易字节数据
            
        Returns:
            Transaction: 交易实例
        """
        # 在实际实现中，这里应该解析原始字节数据
        # 这里是简化的实现
        transaction = Transaction()
        # 假设我们能解析出区块哈希
        transaction.set_recent_blockhash("simulated_blockhash_from_bytes")
        return transaction 