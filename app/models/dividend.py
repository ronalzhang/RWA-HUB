from datetime import datetime
from .. import db

class DividendRecord(db.Model):
    """分红记录模型"""
    __tablename__ = 'dividend_records'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # 分红金额
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'amount': self.amount,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        } 