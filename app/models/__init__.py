from app.extensions import db
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

# 导入基本模型
from .user import User, UserRole, UserStatus
from .asset import Asset, AssetType
from .trade import Trade, TradeStatus, TradeType
from .income import PlatformIncome, IncomeType
from .dividend import Dividend, DividendRecord

# 从admin.py导入管理相关模型
from .admin import (
    AdminUser, SystemConfig, CommissionSetting, 
    DistributionLevel, UserReferral, CommissionRecord, AdminOperationLog,
    DashboardStats
)

# 导入新的分销模型，用不同的名称避免冲突
from .referral import UserReferral as NewUserReferral, CommissionRecord as NewCommissionRecord, DistributionSetting

# 兼容旧版本
from .commission import Commission

# 导出所有模型
__all__ = [
    'db', 'Asset', 'AssetType', 'DividendRecord', 'Dividend', 
    'Trade', 'TradeType', 'User', 'UserRole', 'UserStatus', 
    'Commission', 'AdminUser', 'SystemConfig', 'CommissionSetting',
    'DistributionLevel', 'UserReferral', 'CommissionRecord', 'AdminOperationLog',
    'DashboardStats'
]
