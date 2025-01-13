from app import db
from datetime import datetime, UTC

class Trade(db.Model):
    """交易记录模型"""
    __tablename__ = 'trades'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # buy 或 sell
    amount = db.Column(db.Integer, nullable=False)  # 交易数量
    price = db.Column(db.Float, nullable=False)  # 交易价格
    trader_address = db.Column(db.String(42), nullable=False)  # 交易者钱包地址
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    is_self_trade = db.Column(db.Boolean, nullable=False, default=False)  # 是否是自交易
    
    def to_dict(self):
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'type': self.type,
            'amount': self.amount,
            'price': self.price,
            'trader_address': self.trader_address,
            'created_at': self.created_at.isoformat(),
            'is_self_trade': self.is_self_trade
        } 