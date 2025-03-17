from datetime import datetime
from app.extensions import db
from sqlalchemy.sql import func

class Commission(db.Model):
    """佣金模型（保留兼容旧版本）"""
    __tablename__ = 'commissions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    asset_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(15, 6), nullable=False)
    tx_hash = db.Column(db.String(80), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Commission {self.id} - {self.amount} ETH>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'asset_id': self.asset_id,
            'amount': float(self.amount),
            'tx_hash': self.tx_hash,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        } 