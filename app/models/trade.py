import enum
from datetime import datetime
from .. import db
from sqlalchemy.orm import validates

class TradeType(enum.Enum):
    BUY = 'buy'    # 购买
    SELL = 'sell'  # 出售

class Trade(db.Model):
    __tablename__ = 'trades'
    __table_args__ = (
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    trader_address = db.Column(db.String(42), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_self_trade = db.Column(db.Boolean, nullable=False, default=False)

    # 关联关系
    asset = db.relationship('app.models.asset.Asset', backref=db.backref('trades', lazy=True))

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
        if value <= 0:
            raise ValueError('Trade price must be greater than 0')
        return value

    def to_dict(self):
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'type': self.type,
            'amount': self.amount,
            'price': self.price,
            'trader_address': self.trader_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_self_trade': self.is_self_trade
        } 