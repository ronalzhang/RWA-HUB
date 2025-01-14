from datetime import datetime
from app import db

class Dividend(db.Model):
    """分红记录表"""
    __tablename__ = 'dividends'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    total_amount = db.Column(db.Numeric(20, 6), nullable=False, comment='分红总金额(USDC)')
    created_at = db.Column(db.Date, nullable=False, default=datetime.utcnow, comment='分红日期')
    tx_hash = db.Column(db.String(66), nullable=False, unique=True, comment='交易哈希')
    
    def to_dict(self):
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'total_amount': float(self.total_amount),
            'created_at': self.created_at.strftime('%Y-%m-%d'),
            'tx_hash': self.tx_hash
        } 