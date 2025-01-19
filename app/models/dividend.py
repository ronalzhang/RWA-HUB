from .. import db
from datetime import datetime

class DividendRecord(db.Model):
    """分红记录模型"""
    __tablename__ = 'dividend_records'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)  # 总分红金额
    actual_amount = db.Column(db.Float, nullable=False)  # 实际分红金额
    platform_fee = db.Column(db.Float, nullable=False)  # 平台手续费
    holders_count = db.Column(db.Integer, nullable=False)  # 持有人数
    gas_used = db.Column(db.Integer)  # gas消耗
    tx_hash = db.Column(db.String(66), nullable=False)  # 交易哈希
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # 关联关系
    asset = db.relationship('Asset', backref=db.backref('dividend_records', lazy=True))

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'total_amount': float(self.total_amount),
            'actual_amount': float(self.actual_amount),
            'platform_fee': float(self.platform_fee),
            'holders_count': self.holders_count,
            'gas_used': self.gas_used,
            'tx_hash': self.tx_hash,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } 