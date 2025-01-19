from .. import db
from datetime import datetime
from sqlalchemy.orm import validates
from sqlalchemy import Index, CheckConstraint
import re

class DividendRecord(db.Model):
    """分红记录模型"""
    __tablename__ = 'dividend_records'
    __table_args__ = (
        Index('ix_dividend_records_asset_id', 'asset_id'),  # 资产ID索引
        Index('ix_dividend_records_created_at', 'created_at'),  # 创建时间索引
        CheckConstraint('total_amount >= 10000', name='ck_total_amount_min'),  # 最小分红金额10000
        CheckConstraint('platform_fee = total_amount * 0.015', name='ck_platform_fee_rate'),  # 平台费用1.5%
        CheckConstraint('actual_amount = total_amount - platform_fee', name='ck_actual_amount'),  # 实际分配金额
        {'extend_existing': True}  # 放在元组的最后
    )

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)  # 总分红金额
    actual_amount = db.Column(db.Float, nullable=False)  # 实际分红金额
    platform_fee = db.Column(db.Float, nullable=False)  # 平台手续费
    holders_count = db.Column(db.Integer, nullable=False)  # 持有人数
    gas_used = db.Column(db.Integer)  # gas消耗
    tx_hash = db.Column(db.String(66), nullable=False)  # 交易哈希
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    PLATFORM_FEE_RATE = 0.015  # 1.5%
    MIN_TOTAL_AMOUNT = 10000  # 最小分红金额

    @validates('total_amount')
    def validate_total_amount(self, key, value):
        if value < self.MIN_TOTAL_AMOUNT:
            raise ValueError(f'分红金额不能小于 {self.MIN_TOTAL_AMOUNT} USDC')
        return value

    @validates('platform_fee')
    def validate_platform_fee(self, key, value):
        expected_fee = self.total_amount * self.PLATFORM_FEE_RATE
        if abs(value - expected_fee) > 0.01:  # 允许0.01的误差
            raise ValueError('平台费用必须是总金额的1.5%')
        return value

    @validates('tx_hash')
    def validate_tx_hash(self, key, value):
        if not re.match(r'^0x[a-fA-F0-9]{64}$', value):
            raise ValueError('Invalid transaction hash format')
        return value

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