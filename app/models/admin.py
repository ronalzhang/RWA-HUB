from app.extensions import db
from datetime import datetime
import json
from sqlalchemy import Index, event, func
from sqlalchemy.exc import SQLAlchemyError
import logging
from .asset import Asset 
from .user import User
from .trade import Trade

class AdminUser(db.Model):
    """管理员用户表"""
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    wallet_address = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(50))
    role = db.Column(db.String(20), default='admin', nullable=False)  # super_admin, admin, operator
    permissions = db.Column(db.Text)  # JSON格式存储具体权限
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 定义索引
    __table_args__ = (
        Index('ix_admin_users_wallet_address', 'wallet_address'),
        Index('ix_admin_users_role', 'role'),
    )
    
    # 建立关联
    operation_logs = db.relationship('AdminOperationLog', backref='admin', lazy='dynamic',
                                    foreign_keys='AdminOperationLog.admin_address',
                                    primaryjoin='AdminUser.wallet_address == AdminOperationLog.admin_address')
    
    def get_permissions(self):
        """获取权限列表"""
        if not self.permissions:
            return []
        try:
            return json.loads(self.permissions)
        except:
            return []
    
    def set_permissions(self, permissions_list):
        """设置权限列表"""
        self.permissions = json.dumps(permissions_list)
    
    def has_permission(self, permission):
        """检查是否有特定权限"""
        perms = self.get_permissions()
        return permission in perms or '*' in perms
    
    def is_super_admin(self):
        """检查是否为超级管理员"""
        return self.role == 'super_admin'
    
    def to_dict(self):
        return {
            'id': self.id,
            'wallet_address': self.wallet_address,
            'username': self.username,
            'role': self.role,
            'permissions': self.get_permissions(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat()
        }


class SystemConfig(db.Model):
    """系统配置表"""
    __tablename__ = 'system_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(50), unique=True, nullable=False)
    config_value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 定义索引
    __table_args__ = (
        Index('ix_system_configs_config_key', 'config_key'),
    )
    
    @classmethod
    def get_value(cls, key, default=None):
        """获取配置值"""
        config = cls.query.filter_by(config_key=key).first()
        if not config:
            return default
        return config.config_value
    
    @classmethod
    def set_value(cls, key, value, description=None):
        """设置配置值"""
        config = cls.query.filter_by(config_key=key).first()
        if not config:
            config = cls(config_key=key, config_value=value, description=description)
            db.session.add(config)
        else:
            config.config_value = value
            if description:
                config.description = description
        db.session.commit()
        return config


class CommissionSetting(db.Model):
    """佣金设置表"""
    __tablename__ = 'commission_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_type_id = db.Column(db.Integer)  # NULL表示全局设置
    commission_rate = db.Column(db.Numeric(5, 2), nullable=False)  # 百分比
    min_amount = db.Column(db.Numeric(18, 8))  # 最低佣金金额
    max_amount = db.Column(db.Numeric(18, 8))  # 最高佣金金额
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.String(100), nullable=False)  # 管理员钱包地址
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 定义索引
    __table_args__ = (
        Index('ix_commission_settings_asset_type_id', 'asset_type_id'),
        Index('ix_commission_settings_is_active', 'is_active'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'asset_type_id': self.asset_type_id,
            'commission_rate': float(self.commission_rate),
            'min_amount': float(self.min_amount) if self.min_amount else None,
            'max_amount': float(self.max_amount) if self.max_amount else None,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat()
        }


class DistributionLevel(db.Model):
    """分销等级表"""
    __tablename__ = 'distribution_levels'
    
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, nullable=False)  # 分销层级
    commission_rate = db.Column(db.Numeric(5, 2), nullable=False)  # 此层级的分佣比例
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 定义索引
    __table_args__ = (
        Index('ix_distribution_levels_level', 'level'),
        Index('ix_distribution_levels_is_active', 'is_active'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'commission_rate': float(self.commission_rate),
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }


class UserReferral(db.Model):
    """用户推荐关系表"""
    __tablename__ = 'user_referrals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_address = db.Column(db.String(100), nullable=False)
    referrer_address = db.Column(db.String(100), nullable=False)
    referral_level = db.Column(db.Integer, default=1, nullable=False)
    referral_code = db.Column(db.String(50))
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # 定义索引
    __table_args__ = (
        Index('ix_user_referrals_user_address', 'user_address'),
        Index('ix_user_referrals_referrer_address', 'referrer_address'),
        Index('ix_user_referrals_referral_code', 'referral_code'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_address': self.user_address,
            'referrer_address': self.referrer_address,
            'referral_level': self.referral_level,
            'referral_code': self.referral_code,
            'joined_at': self.joined_at.isoformat()
        }
    
    @classmethod
    def get_referral_chain(cls, user_address, max_level=None):
        """获取用户的推荐链，从直接推荐人到最上层"""
        if not user_address:
            return []
            
        chain = []
        current_user = user_address
        level = 1
        
        while current_user and (max_level is None or level <= max_level):
            referral = cls.query.filter_by(user_address=current_user).first()
            if not referral:
                break
                
            chain.append({
                'level': level,
                'user_address': referral.user_address,
                'referrer_address': referral.referrer_address,
                'joined_at': referral.joined_at.isoformat()
            })
            
            current_user = referral.referrer_address
            level += 1
            
        return chain
    
    @classmethod
    def get_direct_referrals(cls, referrer_address):
        """获取用户直接推荐的用户列表"""
        if not referrer_address:
            return []
            
        referrals = cls.query.filter_by(referrer_address=referrer_address).all()
        return [r.to_dict() for r in referrals]


class CommissionRecord(db.Model):
    """佣金记录表"""
    __tablename__ = 'commission_records'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(100), nullable=False)  # 关联的交易ID
    asset_id = db.Column(db.Integer)  # 关联的资产ID
    recipient_address = db.Column(db.String(100), nullable=False)  # 佣金接收者
    amount = db.Column(db.Numeric(18, 8), nullable=False)  # 佣金金额
    currency = db.Column(db.String(10), default='USD', nullable=False)
    commission_type = db.Column(db.String(20), nullable=False)  # 'direct', 'referral'
    referral_level = db.Column(db.Integer)  # 分销层级
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'paid', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 定义索引
    __table_args__ = (
        Index('ix_commission_records_transaction_id', 'transaction_id'),
        Index('ix_commission_records_recipient_address', 'recipient_address'),
        Index('ix_commission_records_status', 'status'),
        Index('ix_commission_records_created_at', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'asset_id': self.asset_id,
            'recipient_address': self.recipient_address,
            'amount': float(self.amount),
            'currency': self.currency,
            'commission_type': self.commission_type,
            'referral_level': self.referral_level,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class AdminOperationLog(db.Model):
    """后台操作日志表"""
    __tablename__ = 'admin_operation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_address = db.Column(db.String(100), nullable=False)
    operation_type = db.Column(db.String(50), nullable=False)
    target_table = db.Column(db.String(50))
    target_id = db.Column(db.Integer)
    operation_details = db.Column(db.Text)  # JSON格式存储操作详情
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # 定义索引
    __table_args__ = (
        Index('ix_admin_operation_logs_admin_address', 'admin_address'),
        Index('ix_admin_operation_logs_operation_type', 'operation_type'),
        Index('ix_admin_operation_logs_created_at', 'created_at'),
    )
    
    @classmethod
    def log_operation(cls, admin_address, operation_type, target_table=None, target_id=None, 
                    operation_details=None, ip_address=None):
        """记录管理员操作"""
        if isinstance(operation_details, dict):
            operation_details = json.dumps(operation_details)
            
        log = cls(
            admin_address=admin_address,
            operation_type=operation_type,
            target_table=target_table,
            target_id=target_id,
            operation_details=operation_details,
            ip_address=ip_address
        )
        db.session.add(log)
        db.session.commit()
        return log
    
    def to_dict(self):
        details = None
        if self.operation_details:
            try:
                details = json.loads(self.operation_details)
            except:
                details = self.operation_details
                
        return {
            'id': self.id,
            'admin_address': self.admin_address,
            'operation_type': self.operation_type,
            'target_table': self.target_table,
            'target_id': self.target_id,
            'operation_details': details,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat()
        }


class DashboardStats(db.Model):
    """仪表盘统计数据表 - 用于缓存仪表盘数据，避免每次重新计算"""
    __tablename__ = 'dashboard_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    stat_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    stat_type = db.Column(db.String(50), nullable=False)  # 统计类型: user_count, asset_value, trade_volume 等
    stat_value = db.Column(db.Float, nullable=False)  # 统计值
    stat_period = db.Column(db.String(20), nullable=False)  # 统计周期: daily, weekly, monthly
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 定义索引和约束
    __table_args__ = (
        Index('ix_dashboard_stats_date_type_period', 'stat_date', 'stat_type', 'stat_period', unique=True),
        Index('ix_dashboard_stats_stat_date', 'stat_date'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.stat_date.isoformat(),
            'type': self.stat_type,
            'value': self.stat_value,
            'period': self.stat_period,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def update_daily_stats(cls):
        """更新每日统计数据"""
        today = datetime.utcnow().date()
        
        # 用户总数
        total_users = User.query.count()
        cls._update_stat(today, 'user_count', total_users, 'daily')
        
        # 新增用户数
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        new_users = User.query.filter(User.created_at.between(today_start, today_end)).count()
        cls._update_stat(today, 'new_users', new_users, 'daily')
        
        # 资产总数
        total_assets = Asset.query.count()
        cls._update_stat(today, 'asset_count', total_assets, 'daily')
        
        # 资产总价值
        total_value = db.session.query(func.sum(Asset.total_value)).scalar() or 0
        cls._update_stat(today, 'asset_value', float(total_value), 'daily')
        
        # 当日交易量
        daily_trades = Trade.query.filter(Trade.created_at.between(today_start, today_end)).count()
        cls._update_stat(today, 'trade_count', daily_trades, 'daily')
        
        # 当日交易额
        daily_volume = db.session.query(func.sum(Trade.total)).filter(
            Trade.created_at.between(today_start, today_end)
        ).scalar() or 0
        cls._update_stat(today, 'trade_volume', float(daily_volume), 'daily')
        
        db.session.commit()
    
    @classmethod
    def _update_stat(cls, date, stat_type, value, period):
        """更新或创建统计数据"""
        stat = cls.query.filter_by(
            stat_date=date,
            stat_type=stat_type,
            stat_period=period
        ).first()
        
        if stat:
            stat.stat_value = value
            stat.updated_at = datetime.utcnow()
        else:
            stat = cls(
                stat_date=date,
                stat_type=stat_type,
                stat_value=value,
                stat_period=period
            )
            db.session.add(stat)
    
    @classmethod
    def get_trend_data(cls, stat_type, days=30, period='daily'):
        """获取趋势数据"""
        today = datetime.utcnow().date()
        start_date = today - datetime.timedelta(days=days-1)
        
        stats = cls.query.filter(
            cls.stat_type == stat_type,
            cls.stat_period == period,
            cls.stat_date >= start_date
        ).order_by(cls.stat_date).all()
        
        # 构建日期范围内的所有日期
        date_range = [(today - datetime.timedelta(days=i)).isoformat() for i in range(days-1, -1, -1)]
        values = [0] * days
        
        # 填充有数据的日期
        date_to_index = {date: i for i, date in enumerate(date_range)}
        for stat in stats:
            date_str = stat.stat_date.isoformat()
            if date_str in date_to_index:
                values[date_to_index[date_str]] = stat.stat_value
        
        return {
            'labels': date_range,
            'values': values
        }

    @classmethod
    def update_stats_from_db(cls):
        """直接从数据库表中获取最新统计数据并更新到dashboard_stats表"""
        from app.models.asset import Asset
        from app.models.trade import Trade
        from app.models.user import User
        from sqlalchemy import func
        import logging
        from datetime import datetime
        
        today = datetime.utcnow().date()
        logger = logging.getLogger('app')
        
        try:
            # 用户总数
            total_users = User.query.count()
            cls._update_stat(today, 'user_count', total_users, 'daily')
            logger.info(f"更新用户总数统计: {total_users}")
            
            # 资产总数
            total_assets = Asset.query.count()
            cls._update_stat(today, 'asset_count', total_assets, 'daily')
            logger.info(f"更新资产总数统计: {total_assets}")
            
            # 资产总价值
            total_value = db.session.query(func.sum(Asset.total_value)).scalar() or 0
            cls._update_stat(today, 'asset_value', float(total_value), 'daily')
            logger.info(f"更新资产总价值统计: {total_value}")
            
            # 交易总数
            total_trades = Trade.query.count()
            cls._update_stat(today, 'trade_count', total_trades, 'daily')
            logger.info(f"更新交易总数统计: {total_trades}")
            
            # 交易总额
            total_volume = db.session.query(func.sum(Trade.total)).scalar() or 0
            cls._update_stat(today, 'trade_volume', float(total_volume), 'daily')
            logger.info(f"更新交易总额统计: {total_volume}")
            
            # 新增用户数（简化处理，设为0）
            cls._update_stat(today, 'new_users', 0, 'daily')
            
            db.session.commit()
            logger.info("统计数据更新完成")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"更新统计数据失败: {str(e)}", exc_info=True)
            return False


# 事件监听器 - 自动更新仪表盘统计数据
@event.listens_for(User, 'after_insert')
def user_created(mapper, connection, target):
    """用户创建后，异步更新仪表盘统计"""
    from app.utils.decorators import async_task
    
    @async_task
    def update_stats():
        DashboardStats.update_daily_stats()
    
    update_stats()

@event.listens_for(Asset, 'after_insert')
@event.listens_for(Asset, 'after_update')
def asset_changed(mapper, connection, target):
    """资产变更后，异步更新仪表盘统计"""
    from app.utils.decorators import async_task
    
    @async_task
    def update_stats():
        DashboardStats.update_daily_stats()
    
    update_stats()

@event.listens_for(Trade, 'after_insert')
def trade_created(mapper, connection, target):
    """交易创建后，异步更新仪表盘统计"""
    from app.utils.decorators import async_task
    
    @async_task
    def update_stats():
        DashboardStats.update_daily_stats()
    
    update_stats() 