from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import validates
from app.utils.validation_utils import ValidationUtils, ValidationError

class UserReferral(db.Model):
    """用户推荐关系模型"""
    __tablename__ = 'user_referrals'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_address = db.Column(db.String(64), nullable=False)  # 用户钱包地址
    referrer_address = db.Column(db.String(64), nullable=False)  # 推荐人钱包地址
    referral_level = db.Column(db.Integer, default=1, nullable=False)  # 推荐级别，默认为1
    referral_code = db.Column(db.String(50), nullable=True)  # 推荐码
    referral_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # 推荐时间
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)  # 关联的资产ID
    status = db.Column(db.String(20), default='active', nullable=False)  # 状态: active, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    @validates('user_address', 'referrer_address')
    def validate_address(self, key, address):
        """统一的地址验证和标准化"""
        if not address:
            return address
        
        if not ValidationUtils.validate_wallet_address(address):
            raise ValidationError(f'无效的{key}格式', field=key)
        
        return ValidationUtils.normalize_address(address)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_address': self.user_address,
            'referrer_address': self.referrer_address,
            'referral_level': self.referral_level,
            'referral_code': self.referral_code,
            'referral_time': self.referral_time.isoformat() if self.referral_time else None,
            'asset_id': self.asset_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CommissionRecord(db.Model):
    """佣金记录模型"""
    __tablename__ = 'commission_records'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('trades.id'), nullable=False)  # 关联的交易ID
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)  # 关联的资产ID
    recipient_address = db.Column(db.String(64), nullable=False)  # 佣金接收者地址
    amount = db.Column(db.Float, nullable=False)  # 佣金金额
    currency = db.Column(db.String(10), default='USDC', nullable=False)  # 货币单位
    commission_type = db.Column(db.String(20), nullable=False)  # 'platform', 'referral_1', 'referral_2', 'referral_3'
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'paid', 'failed'
    tx_hash = db.Column(db.String(100))  # 佣金支付交易哈希
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @validates('recipient_address')
    def validate_address(self, key, address):
        """在保存前处理地址，保持ETH地址小写，SOL地址保持原始大小写"""
        if not address:
            return address
            
        # ETH地址转小写，SOL地址保持原样
        if address.startswith('0x'):
            return address.lower()
        return address
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'asset_id': self.asset_id,
            'recipient_address': self.recipient_address,
            'amount': self.amount,
            'currency': self.currency,
            'commission_type': self.commission_type,
            'status': self.status,
            'tx_hash': self.tx_hash,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# 分销佣金设置模型
class DistributionSetting(db.Model):
    """分销佣金设置模型"""
    __tablename__ = 'distribution_settings'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, nullable=False)  # 分销层级 1,2,3
    commission_rate = db.Column(db.Float, nullable=False)  # 佣金比例，小数形式，如0.3表示30%
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'level': self.level,
            'commission_rate': self.commission_rate,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 