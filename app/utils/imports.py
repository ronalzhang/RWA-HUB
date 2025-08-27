"""
统一导入模块
减少重复的导入语句，提供常用模型和工具的统一导入
"""

# 数据库相关
from app.extensions import db
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.orm import Query
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# 核心模型
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.trade import Trade, TradeStatus, TradeType
from app.models.user import User, UserRole, UserStatus
from app.models.admin import AdminUser, SystemConfig, CommissionSetting
from app.models.referral import UserReferral, CommissionRecord
from app.models.commission_config import UserCommissionBalance, CommissionConfig
from app.models.dividend import DividendRecord
from app.models.holding import Holding
from app.models.shortlink import ShortLink
from app.models.share_message import ShareMessage
from app.models.pending_payment import PendingPayment
from app.models.commission_withdrawal import CommissionWithdrawal

# Flask相关
from flask import (
    Blueprint, jsonify, request, g, current_app, session, 
    url_for, flash, redirect, render_template, abort, Response
)

# 工具类
from app.utils.validation_utils import ValidationUtils, ValidationError
from app.utils.data_converters import (
    AssetDataConverter, TradeDataConverter, UserDataConverter, 
    CommissionDataConverter, DataConverter
)
from app.utils.error_handler import error_handler, create_error_response, log_error
from app.utils.decorators import (
    api_endpoint, handle_api_errors, require_wallet_address, 
    require_admin_wallet, validate_json_request
)
from app.utils.query_helpers import (
    AssetQueryHelper, TradeQueryHelper, UserQueryHelper, 
    ReferralQueryHelper, QueryBuilder, query_builder
)

# 服务类
from app.services.authentication_service import AuthenticationService

from app.services.unlimited_referral_system import UnlimitedReferralSystem
from app.services.data_consistency_manager import DataConsistencyManager

# 区块链相关
from app.blockchain.solana_service import (
    validate_solana_address, execute_transfer_transaction,
    get_solana_connection, check_transaction_status
)

# 标准库
import json
import os
import uuid
import logging
import traceback
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Union, Tuple
from functools import wraps
from collections import defaultdict

# 日志记录器
logger = logging.getLogger(__name__)

# 常用的模型映射
MODELS = {
    'asset': Asset,
    'trade': Trade,
    'user': User,
    'admin': AdminUser,
    'referral': UserReferral,
    'commission': CommissionRecord,
    'balance': UserCommissionBalance,
    'dividend': DividendRecord,
    'holding': Holding,
    'shortlink': ShortLink,
    'share_message': ShareMessage,
    'pending_payment': PendingPayment,
    'system_config': SystemConfig
}

# 常用的状态枚举
STATUS_ENUMS = {
    'asset_status': AssetStatus,
    'asset_type': AssetType,
    'trade_status': TradeStatus,
    'trade_type': TradeType,
    'user_role': UserRole,
    'user_status': UserStatus
}

# 常用的查询助手
QUERY_HELPERS = {
    'asset': AssetQueryHelper,
    'trade': TradeQueryHelper,
    'user': UserQueryHelper,
    'referral': ReferralQueryHelper
}

# 常用的数据转换器
DATA_CONVERTERS = {
    'asset': AssetDataConverter,
    'trade': TradeDataConverter,
    'user': UserDataConverter,
    'commission': CommissionDataConverter,
    'general': DataConverter
}


def get_model(model_name: str):
    """获取模型类"""
    return MODELS.get(model_name.lower())


def get_status_enum(enum_name: str):
    """获取状态枚举"""
    return STATUS_ENUMS.get(enum_name.lower())


def get_query_helper(helper_name: str):
    """获取查询助手"""
    return QUERY_HELPERS.get(helper_name.lower())


def get_data_converter(converter_name: str):
    """获取数据转换器"""
    return DATA_CONVERTERS.get(converter_name.lower())


# 便捷的导入函数
def import_models(*model_names):
    """批量导入模型"""
    models = {}
    for name in model_names:
        model = get_model(name)
        if model:
            models[name] = model
    return models


def import_helpers(*helper_names):
    """批量导入查询助手"""
    helpers = {}
    for name in helper_names:
        helper = get_query_helper(name)
        if helper:
            helpers[name] = helper
    return helpers


def import_converters(*converter_names):
    """批量导入数据转换器"""
    converters = {}
    for name in converter_names:
        converter = get_data_converter(name)
        if converter:
            converters[name] = converter
    return converters


# 常用的组合导入
def import_common_api():
    """导入API开发常用的模块"""
    return {
        'models': import_models('asset', 'trade', 'user'),
        'helpers': import_helpers('asset', 'trade', 'user'),
        'converters': import_converters('asset', 'trade', 'user'),
        'decorators': {
            'api_endpoint': api_endpoint,
            'handle_errors': handle_api_errors,
            'require_wallet': require_wallet_address,
            'require_admin': require_admin_wallet
        },
        'utils': {
            'create_error': create_error_response,
            'log_error': log_error,
            'validate': ValidationUtils
        }
    }


def import_common_admin():
    """导入管理后台常用的模块"""
    return {
        'models': import_models('asset', 'trade', 'user', 'admin'),
        'helpers': import_helpers('asset', 'trade', 'user'),
        'converters': import_converters('asset', 'trade', 'user'),
        'auth': AuthenticationService(),
        'utils': {
            'create_error': create_error_response,
            'log_error': log_error,
            'validate': ValidationUtils
        }
    }


def import_common_service():
    """导入服务层常用的模块"""
    return {
        'models': MODELS,
        'helpers': QUERY_HELPERS,
        'converters': DATA_CONVERTERS,
        'db': db,
        'logger': logger,
        'utils': {
            'validate': ValidationUtils,
            'error_handler': error_handler
        }
    }


# 装饰器：自动导入常用模块
def with_common_imports(import_type='api'):
    """
    装饰器：自动为函数提供常用导入
    
    Args:
        import_type: 导入类型 ('api', 'admin', 'service')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 根据类型导入相应模块
            if import_type == 'api':
                imports = import_common_api()
            elif import_type == 'admin':
                imports = import_common_admin()
            elif import_type == 'service':
                imports = import_common_service()
            else:
                imports = {}
            
            # 将导入的模块作为关键字参数传递给函数
            return func(*args, **kwargs, **imports)
        
        return wrapper
    return decorator


# 上下文管理器：临时导入
class TempImports:
    """临时导入上下文管理器"""
    
    def __init__(self, import_type='api'):
        self.import_type = import_type
        self.imports = None
    
    def __enter__(self):
        if self.import_type == 'api':
            self.imports = import_common_api()
        elif self.import_type == 'admin':
            self.imports = import_common_admin()
        elif self.import_type == 'service':
            self.imports = import_common_service()
        else:
            self.imports = {}
        
        return self.imports
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.imports = None


# 使用示例：
# 
# # 方式1：直接导入
# from app.utils.imports import *
# 
# # 方式2：批量导入
# models = import_models('asset', 'trade', 'user')
# helpers = import_helpers('asset', 'trade')
# 
# # 方式3：使用装饰器
# @with_common_imports('api')
# def my_api_function(**imports):
#     Asset = imports['models']['asset']
#     asset_helper = imports['helpers']['asset']
#     # ... 使用导入的模块
# 
# # 方式4：使用上下文管理器
# with TempImports('api') as imports:
#     Asset = imports['models']['asset']
#     # ... 使用导入的模块