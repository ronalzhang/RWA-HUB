"""
待处理支付管理模型
用于记录需要管理员手动处理的支付任务
"""
from datetime import datetime
from enum import Enum
from app.extensions import db

class PaymentType(Enum):
    """支付类型枚举"""
    WITHDRAWAL = "withdrawal"  # 用户提现
    REFUND = "refund"  # 退款
    COMMISSION = "commission"  # 佣金发放
    DIVIDEND = "dividend"  # 分红发放
    PLATFORM_FEE = "platform_fee"  # 平台费用
    OTHER = "other"  # 其他

class PaymentStatus(Enum):
    """支付状态枚举"""
    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消

class PaymentPriority(Enum):
    """支付优先级枚举"""
    LOW = "low"  # 低优先级
    NORMAL = "normal"  # 普通优先级
    HIGH = "high"  # 高优先级
    URGENT = "urgent"  # 紧急

class PendingPayment(db.Model):
    """待处理支付表"""
    __tablename__ = 'pending_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 基本信息
    payment_type = db.Column(db.String(50), nullable=False, comment='支付类型')
    title = db.Column(db.String(200), nullable=False, comment='支付标题')
    description = db.Column(db.Text, comment='支付描述')
    
    # 金额信息
    amount = db.Column(db.Numeric(20, 8), nullable=False, comment='支付金额')
    token_symbol = db.Column(db.String(20), nullable=False, default='USDC', comment='代币符号')
    
    # 收款信息
    recipient_address = db.Column(db.String(100), nullable=False, comment='收款地址')
    recipient_name = db.Column(db.String(100), comment='收款人名称')
    
    # 关联信息
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='关联用户ID')
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), comment='关联资产ID')
    trade_id = db.Column(db.Integer, db.ForeignKey('trades.id'), comment='关联交易ID')
    reference_id = db.Column(db.String(100), comment='外部引用ID')
    
    # 状态管理
    status = db.Column(db.String(20), nullable=False, default=PaymentStatus.PENDING.value, comment='支付状态')
    priority = db.Column(db.String(20), nullable=False, default=PaymentPriority.NORMAL.value, comment='优先级')
    
    # 处理信息
    processed_by = db.Column(db.String(100), comment='处理人钱包地址')
    processed_at = db.Column(db.DateTime, comment='处理时间')
    tx_hash = db.Column(db.String(100), comment='交易哈希')
    
    # 失败信息
    failure_reason = db.Column(db.Text, comment='失败原因')
    retry_count = db.Column(db.Integer, default=0, comment='重试次数')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    expires_at = db.Column(db.DateTime, comment='过期时间')
    
    # 关联关系
    user = db.relationship('User', backref='pending_payments', lazy=True)
    asset = db.relationship('Asset', backref='pending_payments', lazy=True)
    trade = db.relationship('Trade', backref='pending_payments', lazy=True)
    
    @classmethod
    def create_withdrawal_request(cls, user_id, amount, recipient_address, token_symbol='USDC'):
        """创建提现请求"""
        payment = cls(
            payment_type=PaymentType.WITHDRAWAL.value,
            title=f'用户提现请求 - {amount} {token_symbol}',
            description=f'用户ID: {user_id} 申请提现 {amount} {token_symbol}',
            amount=amount,
            token_symbol=token_symbol,
            recipient_address=recipient_address,
            user_id=user_id,
            priority=PaymentPriority.HIGH.value
        )
        db.session.add(payment)
        db.session.commit()
        return payment
    
    @classmethod
    def create_commission_payment(cls, user_id, amount, recipient_address, reference_id=None):
        """创建佣金发放任务"""
        payment = cls(
            payment_type=PaymentType.COMMISSION.value,
            title=f'佣金发放 - {amount} USDC',
            description=f'用户ID: {user_id} 佣金发放',
            amount=amount,
            token_symbol='USDC',
            recipient_address=recipient_address,
            user_id=user_id,
            reference_id=reference_id,
            priority=PaymentPriority.NORMAL.value
        )
        db.session.add(payment)
        db.session.commit()
        return payment
    
    @classmethod
    def create_refund_payment(cls, user_id, amount, recipient_address, asset_id=None, reason=''):
        """创建退款任务"""
        payment = cls(
            payment_type=PaymentType.REFUND.value,
            title=f'退款处理 - {amount} USDC',
            description=f'退款原因: {reason}',
            amount=amount,
            token_symbol='USDC',
            recipient_address=recipient_address,
            user_id=user_id,
            asset_id=asset_id,
            priority=PaymentPriority.HIGH.value
        )
        db.session.add(payment)
        db.session.commit()
        return payment
    
    @classmethod
    def get_pending_payments(cls, limit=50):
        """获取待处理支付列表"""
        return cls.query.filter_by(status=PaymentStatus.PENDING.value)\
                      .order_by(cls.priority.desc(), cls.created_at.asc())\
                      .limit(limit).all()
    
    @classmethod
    def get_payments_by_status(cls, status, limit=50):
        """根据状态获取支付列表"""
        return cls.query.filter_by(status=status)\
                      .order_by(cls.created_at.desc())\
                      .limit(limit).all()
    
    @classmethod
    def get_urgent_payments(cls):
        """获取紧急支付列表"""
        return cls.query.filter_by(
            status=PaymentStatus.PENDING.value,
            priority=PaymentPriority.URGENT.value
        ).order_by(cls.created_at.asc()).all()
    
    def mark_as_processing(self, processed_by):
        """标记为处理中"""
        self.status = PaymentStatus.PROCESSING.value
        self.processed_by = processed_by
        self.processed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def mark_as_completed(self, tx_hash):
        """标记为已完成"""
        self.status = PaymentStatus.COMPLETED.value
        self.tx_hash = tx_hash
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def mark_as_failed(self, reason):
        """标记为失败"""
        self.status = PaymentStatus.FAILED.value
        self.failure_reason = reason
        self.retry_count += 1
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'payment_type': self.payment_type,
            'title': self.title,
            'description': self.description,
            'amount': float(self.amount),
            'token_symbol': self.token_symbol,
            'recipient_address': self.recipient_address,
            'recipient_name': self.recipient_name,
            'user_id': self.user_id,
            'asset_id': self.asset_id,
            'trade_id': self.trade_id,
            'reference_id': self.reference_id,
            'status': self.status,
            'priority': self.priority,
            'processed_by': self.processed_by,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'tx_hash': self.tx_hash,
            'failure_reason': self.failure_reason,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }