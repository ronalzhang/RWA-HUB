from app.extensions import db
from datetime import datetime

class PlatformIncome(db.Model):
    """平台收入记录模型"""
    __tablename__ = 'platform_income'
    
    id = db.Column(db.Integer, primary_key=True)
    income_type = db.Column(db.String(20), nullable=False, comment='收入类型: trade_fee, onchain_fee, dividend_fee, other')
    amount = db.Column(db.Float, nullable=False, comment='收入金额')
    currency = db.Column(db.String(10), nullable=False, default='USDC', comment='收入币种')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, comment='收入记录创建时间')
    description = db.Column(db.String(255), comment='收入描述')
    transaction_hash = db.Column(db.String(100), comment='交易哈希')
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), comment='关联资产ID')
    
    # 关系
    asset = db.relationship('Asset', backref=db.backref('income_records', lazy=True))
    
    def __init__(self, income_type, amount, currency='USDC', description=None, transaction_hash=None, asset_id=None):
        self.income_type = income_type
        self.amount = amount
        self.currency = currency
        self.description = description
        self.transaction_hash = transaction_hash
        self.asset_id = asset_id
    
    def __repr__(self):
        return f'<PlatformIncome {self.id}: {self.income_type} {self.amount} {self.currency}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'income_type': self.income_type,
            'amount': self.amount,
            'currency': self.currency,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'description': self.description,
            'transaction_hash': self.transaction_hash,
            'asset_id': self.asset_id
        } 