"""
佣金提现记录模型
记录用户的佣金提现申请和处理状态
"""

from datetime import datetime, timedelta
from decimal import Decimal
from app.extensions import db
from sqlalchemy import func


class CommissionWithdrawal(db.Model):
    """佣金提现记录表"""
    __tablename__ = 'commission_withdrawals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_address = db.Column(db.String(64), nullable=False, index=True)  # 申请用户地址
    to_address = db.Column(db.String(64), nullable=False)                # 提现到的钱包地址
    amount = db.Column(db.Numeric(20, 8), nullable=False)                # 提现金额
    currency = db.Column(db.String(10), default='USDC')                  # 币种
    
    # 状态管理
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, processing, completed, failed, cancelled
    
    # 延迟机制
    delay_minutes = db.Column(db.Integer, default=1)                     # 延迟分钟数
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)       # 申请时间
    process_at = db.Column(db.DateTime)                                  # 预计处理时间
    processed_at = db.Column(db.DateTime)                                # 实际处理时间
    
    # 交易信息
    tx_hash = db.Column(db.String(80))                                   # 区块链交易哈希
    gas_fee = db.Column(db.Numeric(20, 8), default=0)                    # 手续费
    actual_amount = db.Column(db.Numeric(20, 8))                         # 实际到账金额
    
    # 备注信息
    note = db.Column(db.Text)                                            # 备注
    admin_note = db.Column(db.Text)                                      # 管理员备注
    failure_reason = db.Column(db.Text)                                  # 失败原因
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保requested_at有值
        if not self.requested_at:
            self.requested_at = datetime.utcnow()
        # 自动计算预计处理时间
        if not self.process_at and self.delay_minutes:
            self.process_at = self.requested_at + timedelta(minutes=self.delay_minutes)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_address': self.user_address,
            'to_address': self.to_address,
            'amount': float(self.amount),
            'currency': self.currency,
            'status': self.status,
            'delay_minutes': self.delay_minutes,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'process_at': self.process_at.isoformat() if self.process_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'tx_hash': self.tx_hash,
            'gas_fee': float(self.gas_fee) if self.gas_fee else 0,
            'actual_amount': float(self.actual_amount) if self.actual_amount else None,
            'note': self.note,
            'admin_note': self.admin_note,
            'failure_reason': self.failure_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def is_ready_to_process(self):
        """检查是否可以处理"""
        if self.status != 'pending':
            return False
        return datetime.utcnow() >= self.process_at
    
    @property
    def remaining_delay_seconds(self):
        """剩余延迟秒数"""
        if self.status != 'pending':
            return 0
        remaining = (self.process_at - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))
    
    def mark_processing(self):
        """标记为处理中"""
        self.status = 'processing'
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def mark_completed(self, tx_hash, actual_amount=None, gas_fee=None):
        """标记为完成"""
        self.status = 'completed'
        self.tx_hash = tx_hash
        self.processed_at = datetime.utcnow()
        if actual_amount is not None:
            self.actual_amount = Decimal(str(actual_amount))
        if gas_fee is not None:
            self.gas_fee = Decimal(str(gas_fee))
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def mark_failed(self, reason):
        """标记为失败"""
        self.status = 'failed'
        self.failure_reason = reason
        self.processed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def cancel(self, reason=None):
        """取消提现"""
        self.status = 'cancelled'
        if reason:
            self.admin_note = reason
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def get_pending_withdrawals():
        """获取待处理的提现记录"""
        return CommissionWithdrawal.query.filter_by(status='pending').all()
    
    @staticmethod
    def get_ready_to_process():
        """获取可以处理的提现记录"""
        now = datetime.utcnow()
        return CommissionWithdrawal.query.filter(
            CommissionWithdrawal.status == 'pending',
            CommissionWithdrawal.process_at <= now
        ).all()
    
    @staticmethod
    def get_user_withdrawals(user_address, limit=20, offset=0):
        """获取用户的提现记录"""
        return CommissionWithdrawal.query.filter_by(user_address=user_address) \
            .order_by(CommissionWithdrawal.created_at.desc()) \
            .offset(offset).limit(limit).all()
    
    @staticmethod
    def get_withdrawal_stats():
        """获取提现统计"""
        total_amount = db.session.query(func.sum(CommissionWithdrawal.amount)).scalar() or 0
        total_count = CommissionWithdrawal.query.count()
        
        pending_amount = db.session.query(func.sum(CommissionWithdrawal.amount)).filter(
            CommissionWithdrawal.status == 'pending'
        ).scalar() or 0
        pending_count = CommissionWithdrawal.query.filter_by(status='pending').count()
        
        completed_amount = db.session.query(func.sum(CommissionWithdrawal.amount)).filter(
            CommissionWithdrawal.status == 'completed'
        ).scalar() or 0
        completed_count = CommissionWithdrawal.query.filter_by(status='completed').count()
        
        return {
            'total': {'amount': float(total_amount), 'count': total_count},
            'pending': {'amount': float(pending_amount), 'count': pending_count},
            'completed': {'amount': float(completed_amount), 'count': completed_count}
        } 