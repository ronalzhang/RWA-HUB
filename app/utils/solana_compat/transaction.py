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
        keys: List[AccountMeta],
        program_id: Any,
        data: bytes = bytes(0),
    ):
        """Initialize instruction."""
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
        # 简化实现，实际应序列化为特定格式
        return bytes([0] * 32) 