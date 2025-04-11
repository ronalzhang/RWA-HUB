import enum
from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import validates
from sqlalchemy import event

class TradeType(enum.Enum):
    BUY = 'buy'    # 购买
    SELL = 'sell'  # 出售

# 添加交易状态枚举
class TradeStatus(enum.Enum):
    PENDING = 'pending'    # 待处理
    COMPLETED = 'completed'  # 已完成
    FAILED = 'failed'  # 失败

class Trade(db.Model):
    """交易记录模型"""
    __tablename__ = 'trades'
    __table_args__ = (
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)  # 改为可空，支持无资产交易如平台费
    type = db.Column(db.String(10), nullable=False)  # buy 或 sell
    amount = db.Column(db.Integer, nullable=False)  # 交易数量
    price = db.Column(db.Float, nullable=False)  # 交易价格
    total = db.Column(db.Float, nullable=True)  # 交易总额
    token_amount = db.Column(db.Float, nullable=True)  # 购买的代币数量
    fee = db.Column(db.Float, nullable=True)  # 交易手续费
    fee_rate = db.Column(db.Float, nullable=True)  # 手续费率
    trader_address = db.Column(db.String(64), nullable=False)  # 交易者钱包地址，支持Solana长度
    tx_hash = db.Column(db.String(100))  # 交易哈希，支持各种区块链
    status = db.Column(db.String(20), default=TradeStatus.PENDING.value)  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    gas_used = db.Column(db.Numeric, nullable=True)  # 交易使用的gas量
    is_self_trade = db.Column(db.Boolean, nullable=False, default=False)  # 是否是自交易(和自己交易)

    # 添加与 Asset 的关系
    asset = db.relationship("Asset", back_populates="trades")

    @validates('type')
    def validate_type(self, key, value):
        if value not in [t.value for t in TradeType]:
            raise ValueError('Invalid trade type')
        return value

    @validates('amount')
    def validate_amount(self, key, value):
        if value <= 0:
            raise ValueError('Trade amount must be greater than 0')
        return value

    @validates('price')
    def validate_price(self, key, value):
        # 对于平台费交易(asset_id为None的情况)，允许price为0
        if hasattr(self, 'asset_id') and self.asset_id is None:
            return value
            
        if value <= 0:
            raise ValueError('Trade price must be greater than 0')
        return value

    @validates('trader_address')
    def validate_trader_address(self, key, address):
        """在保存前处理地址，保持ETH地址小写，SOL地址保持原始大小写"""
        if not address:
            return address
            
        # ETH地址转小写，SOL地址保持原样
        if address.startswith('0x'):
            return address.lower()
        return address

    def to_dict(self):
        """转换为字典"""
        result = {
            'id': self.id,
            'asset_id': self.asset_id,
            'type': self.type,
            'amount': self.amount,
            'price': self.price,
            'token_amount': self.token_amount,
            'total': self.total if self.total is not None else self.amount * self.price,
            'fee': self.fee,
            'fee_rate': self.fee_rate,
            'trader_address': self.trader_address,
            'tx_hash': self.tx_hash,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'gas_used': float(self.gas_used) if self.gas_used else None,
            'is_self_trade': self.is_self_trade
        }
        return result 