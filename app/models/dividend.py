from datetime import datetime
from app.extensions import db

class DividendRecord(db.Model):
    """分红记录"""
    __tablename__ = 'dividend_records'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    amount = db.Column(db.Numeric(20, 6), nullable=False)  # 分红金额
    distributor_address = db.Column(db.String(44), nullable=False)  # 发起人地址
    transaction_hash = db.Column(db.String(88))  # 交易哈希
    interval = db.Column(db.Integer, nullable=False)  # 分红间隔（秒）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    asset = db.relationship("Asset", back_populates="dividend_records")
    distributions = db.relationship('DividendDistribution', backref='dividend_record', lazy=True)
    
    @classmethod
    def create(cls, asset_id, amount, distributor_address, interval):
        """创建分红记录"""
        record = cls(
            asset_id=asset_id,
            amount=amount,
            distributor_address=distributor_address,
            interval=interval
        )
        db.session.add(record)
        db.session.commit()
        return record
    
    def update_transaction_hash(self, transaction_hash):
        """更新交易哈希"""
        self.transaction_hash = transaction_hash
        db.session.commit()
    
    @classmethod
    def get_by_asset(cls, asset_id):
        """获取资产的所有分红记录"""
        return cls.query.filter_by(asset_id=asset_id).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_count_by_asset(cls, asset_id):
        """获取资产的分红记录数量"""
        return cls.query.filter_by(asset_id=asset_id).count()
    
    @classmethod
    def get_total_amount_by_asset(cls, asset_id):
        """获取资产的总分红金额"""
        records = cls.query.filter_by(asset_id=asset_id).all()
        return sum(record.amount for record in records)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'amount': float(self.amount),
            'distributor_address': self.distributor_address,
            'transaction_hash': self.transaction_hash,
            'interval': self.interval,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class DividendDistribution(db.Model):
    """分红分配记录"""
    __tablename__ = 'dividend_distributions'
    
    id = db.Column(db.Integer, primary_key=True)
    dividend_record_id = db.Column(db.Integer, db.ForeignKey('dividend_records.id'), nullable=False)
    holder_address = db.Column(db.String(44), nullable=False)  # 持有人地址
    amount = db.Column(db.Numeric(20, 6), nullable=False)  # 分配金额
    status = db.Column(db.String(20), nullable=False, default='pending')  # 状态：pending/claimed
    claimed_at = db.Column(db.DateTime)  # 领取时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def create(cls, dividend_record_id, holder_address, amount):
        """创建分配记录"""
        distribution = cls(
            dividend_record_id=dividend_record_id,
            holder_address=holder_address,
            amount=amount
        )
        db.session.add(distribution)
        db.session.commit()
        return distribution
    
    def claim(self):
        """标记为已领取"""
        self.status = 'claimed'
        self.claimed_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'dividend_record_id': self.dividend_record_id,
            'holder_address': self.holder_address,
            'amount': float(self.amount),
            'status': self.status,
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class WithdrawalRequest(db.Model):
    """提现申请"""
    __tablename__ = 'withdrawal_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_address = db.Column(db.String(44), nullable=False)  # 用户地址
    amount = db.Column(db.Numeric(20, 6), nullable=False)  # 提现金额
    type = db.Column(db.String(20), nullable=False)  # 类型：dividend/reward
    status = db.Column(db.String(20), nullable=False, default='pending')  # 状态：pending/processing/completed/failed
    transaction_hash = db.Column(db.String(88))  # 交易哈希
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def create(cls, user_address, amount, type):
        """创建提现申请"""
        request = cls(
            user_address=user_address,
            amount=amount,
            type=type
        )
        db.session.add(request)
        db.session.commit()
        return request
    
    def update_transaction_hash(self, transaction_hash):
        """更新交易哈希"""
        self.transaction_hash = transaction_hash
        self.status = 'processing'
        db.session.commit()
    
    def complete(self):
        """标记为已完成"""
        self.status = 'completed'
        db.session.commit()
    
    def fail(self):
        """标记为失败"""
        self.status = 'failed'
        db.session.commit()
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_address': self.user_address,
            'amount': float(self.amount),
            'type': self.type,
            'status': self.status,
            'transaction_hash': self.transaction_hash,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Dividend(db.Model):
    """资产分红模型"""
    __tablename__ = 'dividends'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    amount = db.Column(db.Numeric(20, 6), nullable=False)  # 使用NUMERIC类型存储金额，保留6位小数
    payment_token = db.Column(db.String(10), default='USDC') # 支付代币,默认为USDC
    dividend_date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending') # pending, processing, confirmed, failed
    transaction_hash = db.Column(db.String(255))
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 定义与Asset模型的关系
    asset = db.relationship('Asset', back_populates="dividends") # 修正 back_populates 指向 Asset.dividends

    def __repr__(self):
        return f'<Dividend {self.id} for Asset {self.asset_id}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'amount': float(self.amount),
            'payment_token': self.payment_token,
            'dividend_date': self.dividend_date.strftime('%Y-%m-%d %H:%M:%S') if self.dividend_date else None,
            'description': self.description,
            'status': self.status,
            'transaction_hash': self.transaction_hash,
            'error_message': self.error_message,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        } 