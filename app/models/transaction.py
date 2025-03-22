import enum
from datetime import datetime
from app.extensions import db
from sqlalchemy import Index

class TransactionType(enum.Enum):
    TRANSFER = 1           # 转账
    PURCHASE = 2           # 购买资产
    STAKING = 3            # 质押
    UNSTAKING = 4          # 解除质押
    CLAIM_REWARD = 5       # 领取奖励
    MINT_TOKEN = 6         # 铸造代币
    FEE = 7                # 手续费
    REFUND = 8             # 退款
    DIVIDEND = 9           # 分红
    ASSET_LISTING = 10     # 资产上架
    OTHER = 99             # 其他

class TransactionStatus(enum.Enum):
    PENDING = 1    # 待确认
    CONFIRMED = 2  # 已确认
    FAILED = 3     # 失败
    CANCELLED = 4  # 已取消

class Transaction(db.Model):
    """区块链交易记录"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    tx_hash = db.Column(db.String(100), unique=True, index=True)
    tx_type = db.Column(db.Integer, nullable=False)  # TransactionType枚举值
    status = db.Column(db.Integer, default=TransactionStatus.PENDING.value)
    
    # 区块链相关信息
    blockchain = db.Column(db.String(20), nullable=False, default='solana')  # 'solana', 'ethereum'等
    amount = db.Column(db.Float, nullable=True)
    token_address = db.Column(db.String(64), nullable=True)
    token_name = db.Column(db.String(50), nullable=True)
    
    # 交易相关方
    from_address = db.Column(db.String(100), nullable=True, index=True)
    to_address = db.Column(db.String(100), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    
    # 附加信息
    fee = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON格式的详细信息
    
    # 索引
    __table_args__ = (
        Index('idx_tx_user_asset', 'user_id', 'asset_id'),
        Index('idx_tx_status_type', 'status', 'tx_type'),
    )
    
    def __repr__(self):
        return f"<Transaction {self.id}: {self.tx_hash}>"
    
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