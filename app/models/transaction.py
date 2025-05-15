"""
交易模型 - 记录支付和转账相关信息
"""

from app.extensions import db
from datetime import datetime
from enum import Enum

class TransactionStatus(Enum):
    """交易状态枚举"""
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class TransactionType(Enum):
    """交易类型枚举"""
    PAYMENT = 'payment'
    TRANSFER = 'transfer'
    FEE = 'fee'
    REFUND = 'refund'
    OTHER = 'other'

class Transaction(db.Model):
    """交易模型"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    from_address = db.Column(db.String(255), nullable=False, index=True)
    to_address = db.Column(db.String(255), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    token_symbol = db.Column(db.String(50), nullable=False)
    signature = db.Column(db.String(255), nullable=True, unique=True)
    status = db.Column(db.String(50), nullable=False, default=TransactionStatus.PENDING.value)
    tx_type = db.Column(db.String(50), nullable=False, default=TransactionType.PAYMENT.value)
    data = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Transaction {self.id}: {self.from_address} -> {self.to_address}, {self.amount} {self.token_symbol}>'
        
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'amount': self.amount,
            'token_symbol': self.token_symbol,
            'signature': self.signature,
            'status': self.status,
            'tx_type': self.tx_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def type_name(self):
        """返回交易类型的名称"""
        try:
            return TransactionType(self.tx_type).name
        except:
            return "UNKNOWN"
    
    @property
    def status_name(self):
        """返回交易状态的名称"""
        try:
            return TransactionStatus(self.status).name
        except:
            return "UNKNOWN"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'tx_hash': self.tx_hash,
            'tx_type': self.tx_type,
            'tx_type_name': self.type_name,
            'status': self.status,
            'status_name': self.status_name,
            'blockchain': self.blockchain,
            'amount': self.amount,
            'token_address': self.token_address,
            'token_name': self.token_name,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'user_id': self.user_id,
            'asset_id': self.asset_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'fee': self.fee,
            'notes': self.notes
        } 