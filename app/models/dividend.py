from datetime import datetime
from app.extensions import db

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

class Dividend(db.Model):
    """资产分红模型"""
    __tablename__ = 'dividends'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # 分红总金额
    distribution_date = db.Column(db.DateTime, nullable=False)  # 分红日期
    record_date = db.Column(db.DateTime, nullable=False)  # 登记日期
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, completed, cancelled
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    transaction_hash = db.Column(db.String(100))  # 区块链交易哈希
    
    # 关系
    asset = db.relationship('Asset', backref=db.backref('dividends', lazy=True))
    
    def __repr__(self):
        return f'<Dividend {self.id}: {self.amount} for Asset {self.asset_id}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'amount': self.amount,
            'distribution_date': self.distribution_date.strftime('%Y-%m-%d %H:%M:%S') if self.distribution_date else None,
            'record_date': self.record_date.strftime('%Y-%m-%d %H:%M:%S') if self.record_date else None,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'transaction_hash': self.transaction_hash
        } 