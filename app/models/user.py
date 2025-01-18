import enum
from datetime import datetime
from app import db
from sqlalchemy.orm import validates
import re
import json

class UserRole(enum.Enum):
    USER = 'user'          # 普通用户
    ADMIN = 'admin'        # 管理员
    SUPER_ADMIN = 'super'  # 超级管理员

class UserStatus(enum.Enum):
    ACTIVE = 'active'    # 活跃
    INACTIVE = 'inactive'  # 未激活
    BANNED = 'banned'    # 禁用

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    eth_address = db.Column(db.String(42), unique=True)
    nonce = db.Column(db.String(100))
    role = db.Column(db.String(20), nullable=False, default=UserRole.USER.value)
    status = db.Column(db.String(20), nullable=False, default=UserStatus.ACTIVE.value)
    settings = db.Column(db.Text, default='{}')  # JSON格式存储用户设置
    is_active = db.Column(db.Boolean, default=True)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    @validates('eth_address')
    def validate_eth_address(self, key, value):
        if value:
            if not re.match(r'^0x[a-fA-F0-9]{40}$', value):
                raise ValueError('Invalid Ethereum address format')
        return value

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
        """转换为字典格式"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'eth_address': self.eth_address,
            'role': self.role,
            'status': self.status,
            'settings': self.get_settings(),
            'is_active': self.is_active,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }