import enum
from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import validates
import re
import json
from sqlalchemy import func, or_
from app.utils.validation_utils import ValidationUtils, ValidationError

class UserRole(enum.Enum):
    USER = 'user'          # 普通用户
    ADMIN = 'admin'        # 管理员
    SUPER_ADMIN = 'super'  # 超级管理员

class UserStatus(enum.Enum):
    ACTIVE = 'active'    # 活跃
    INACTIVE = 'inactive'  # 未激活
    BANNED = 'banned'    # 禁用

# 辅助函数，比较两个钱包地址是否相同（不区分大小写）
def is_same_wallet_address(address1, address2):
    if not address1 or not address2:
        return False
    
    # 如果是以太坊地址（0x开头），则不区分大小写
    if address1.startswith('0x') and address2.startswith('0x'):
        return address1.lower() == address2.lower()
    
    # 对于其他类型地址（如Solana），需要区分大小写
    return address1 == address2

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    eth_address = db.Column(db.String(64), unique=True)
    solana_address = db.Column(db.String(64), unique=True)  # Solana钱包地址
    wallet_type = db.Column(db.String(20), default='ethereum')  # 钱包类型
    nonce = db.Column(db.String(100))
    role = db.Column(db.String(20), nullable=False, default=UserRole.USER.value)
    status = db.Column(db.String(20), nullable=False, default=UserStatus.ACTIVE.value)
    settings = db.Column(db.Text, default='{}')  # JSON格式存储用户设置
    is_active = db.Column(db.Boolean, default=True)
    
    # 分销商相关字段（所有用户都是分销商）
    is_distributor = db.Column(db.Boolean, default=True)   # 所有用户都是分销商
    is_verified = db.Column(db.Boolean, default=False)     # 是否已认证
    is_blocked = db.Column(db.Boolean, default=False)      # 是否被冻结
    referrer_address = db.Column(db.String(64))            # 推荐人地址
    
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    @validates('eth_address')
    def validate_eth_address(self, key, value):
        if value and not ValidationUtils.validate_ethereum_address(value):
            raise ValidationError('无效的以太坊地址格式', field='eth_address')
        return ValidationUtils.normalize_address(value) if value else value

    @validates('role')
    def validate_role(self, key, value):
        if value not in [r.value for r in UserRole]:
            raise ValueError('Invalid user role')
        return value

    @validates('status')
    def validate_status(self, key, value):
        if value not in [s.value for s in UserStatus]:
            raise ValueError('Invalid user status')
        return value

    @validates('settings')
    def validate_settings(self, key, value):
        if value:
            try:
                if isinstance(value, str):
                    json.loads(value)
                elif isinstance(value, dict):
                    value = json.dumps(value)
                else:
                    raise ValueError
            except:
                raise ValueError('Invalid settings format')
        return value

    def get_settings(self):
        """获取用户设置"""
        try:
            return json.loads(self.settings)
        except:
            return {}

    def update_settings(self, new_settings):
        """更新用户设置"""
        if not isinstance(new_settings, dict):
            raise ValueError('Settings must be a dictionary')
        
        current_settings = self.get_settings()
        current_settings.update(new_settings)
        self.settings = json.dumps(current_settings)

    def to_dict(self):
        """转换为字典格式 - 使用统一的数据转换器"""
        from app.utils.data_converters import UserDataConverter
        return UserDataConverter.to_api_format(self)