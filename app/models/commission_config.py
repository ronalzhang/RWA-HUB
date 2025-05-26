"""
佣金配置模型
管理分佣规则、分享设置等配置信息
"""
from datetime import datetime
from decimal import Decimal
from app.extensions import db
import json

class CommissionConfig(db.Model):
    """佣金配置表"""
    __tablename__ = 'commission_config'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False)  # 配置键
    config_value = db.Column(db.Text, nullable=False)                    # 配置值(JSON格式)
    description = db.Column(db.String(255))                              # 配置描述
    is_active = db.Column(db.Boolean, default=True)                      # 是否启用
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_value(self):
        """获取配置值"""
        try:
            return json.loads(self.config_value)
        except:
            return self.config_value
    
    def set_value(self, value):
        """设置配置值"""
        if isinstance(value, (dict, list)):
            self.config_value = json.dumps(value, ensure_ascii=False)
        else:
            self.config_value = str(value)
    
    @staticmethod
    def get_config(key, default=None):
        """获取配置"""
        config = CommissionConfig.query.filter_by(config_key=key, is_active=True).first()
        if config:
            return config.get_value()
        return default
    
    @staticmethod
    def set_config(key, value, description=None):
        """设置配置"""
        config = CommissionConfig.query.filter_by(config_key=key).first()
        if not config:
            config = CommissionConfig(config_key=key)
            if description:
                config.description = description
            db.session.add(config)
        
        config.set_value(value)
        config.updated_at = datetime.utcnow()
        db.session.commit()
        return config

class UserCommissionBalance(db.Model):
    """用户佣金余额表"""
    __tablename__ = 'user_commission_balance'
    
    id = db.Column(db.Integer, primary_key=True)
    user_address = db.Column(db.String(64), unique=True, nullable=False)  # 用户地址
    total_earned = db.Column(db.Numeric(20, 8), default=0)                # 总收益
    available_balance = db.Column(db.Numeric(20, 8), default=0)           # 可用余额
    withdrawn_amount = db.Column(db.Numeric(20, 8), default=0)            # 已提现金额
    frozen_amount = db.Column(db.Numeric(20, 8), default=0)               # 冻结金额
    currency = db.Column(db.String(10), default='USDC')                   # 币种
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'user_address': self.user_address,
            'total_earned': float(self.total_earned),
            'available_balance': float(self.available_balance),
            'withdrawn_amount': float(self.withdrawn_amount),
            'frozen_amount': float(self.frozen_amount),
            'currency': self.currency,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    @staticmethod
    def get_balance(user_address):
        """获取用户佣金余额"""
        balance = UserCommissionBalance.query.filter_by(user_address=user_address).first()
        if not balance:
            # 创建新的余额记录
            balance = UserCommissionBalance(user_address=user_address)
            db.session.add(balance)
            db.session.commit()
        return balance
    
    @staticmethod
    def add_balance(user_address, amount, currency='USDC'):
        """添加用户佣金余额（简化版本，直接调用update_balance）"""
        return UserCommissionBalance.update_balance(user_address, amount, 'add')
    
    @staticmethod
    def subtract_balance(user_address, amount):
        """减少用户佣金余额"""
        balance = UserCommissionBalance.get_balance(user_address)
        amount_decimal = Decimal(str(amount))
        
        if balance.available_balance >= amount_decimal:
            balance.available_balance -= amount_decimal
            db.session.commit()
            return balance
        else:
            raise ValueError('余额不足')
    
    @staticmethod
    def freeze_balance(user_address, amount):
        """冻结用户佣金余额"""
        return UserCommissionBalance.update_balance(user_address, amount, 'freeze')
    
    @staticmethod
    def unfreeze_balance(user_address, amount):
        """解冻用户佣金余额"""
        return UserCommissionBalance.update_balance(user_address, amount, 'unfreeze')
    
    @staticmethod
    def withdraw_balance(user_address, amount):
        """提现用户佣金余额"""
        return UserCommissionBalance.update_balance(user_address, amount, 'withdraw')
    
    @staticmethod
    def get_total_balance():
        """获取所有用户的总余额"""
        from sqlalchemy import func
        result = db.session.query(
            func.sum(UserCommissionBalance.total_earned).label('total_earned'),
            func.sum(UserCommissionBalance.available_balance).label('available_balance'),
            func.sum(UserCommissionBalance.withdrawn_amount).label('withdrawn_amount'),
            func.sum(UserCommissionBalance.frozen_amount).label('frozen_amount')
        ).first()
        
        return {
            'total_earned': float(result.total_earned or 0),
            'available_balance': float(result.available_balance or 0),
            'withdrawn_amount': float(result.withdrawn_amount or 0),
            'frozen_amount': float(result.frozen_amount or 0)
        }
    
    @staticmethod
    def get_user_count():
        """获取有佣金记录的用户数量"""
        return UserCommissionBalance.query.filter(
            UserCommissionBalance.total_earned > 0
        ).count()
    
    @staticmethod
    def update_balance(user_address, amount, operation='add'):
        """更新用户佣金余额"""
        balance = UserCommissionBalance.get_balance(user_address)
        
        if operation == 'add':
            balance.total_earned += Decimal(str(amount))
            balance.available_balance += Decimal(str(amount))
        elif operation == 'withdraw':
            amount_decimal = Decimal(str(amount))
            if balance.available_balance >= amount_decimal:
                balance.available_balance -= amount_decimal
                balance.withdrawn_amount += amount_decimal
            else:
                raise ValueError('余额不足')
        elif operation == 'freeze':
            amount_decimal = Decimal(str(amount))
            if balance.available_balance >= amount_decimal:
                balance.available_balance -= amount_decimal
                balance.frozen_amount += amount_decimal
            else:
                raise ValueError('余额不足')
        elif operation == 'unfreeze':
            amount_decimal = Decimal(str(amount))
            if balance.frozen_amount >= amount_decimal:
                balance.frozen_amount -= amount_decimal
                balance.available_balance += amount_decimal
            else:
                raise ValueError('冻结金额不足')
        
        db.session.commit()
        return balance 