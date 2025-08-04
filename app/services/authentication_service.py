"""
统一的身份验证服务
优先从数据库验证管理员，配置文件作为备用
"""

from flask import current_app, g
from app.models.admin import AdminUser
from sqlalchemy import func
import logging

class AuthenticationService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.admin_addresses = self._load_admin_addresses()
    
    def verify_admin_wallet(self, wallet_address: str) -> bool:
        """验证管理员钱包地址"""
        if not wallet_address:
            self.logger.warning("未提供钱包地址")
            return False
            
        self.logger.info(f"验证管理员钱包地址: {wallet_address}")
        
        # 1. 优先从数据库查询
        try:
            admin = self._query_admin_from_database(wallet_address)
            if admin:
                self.logger.info(f"数据库验证成功 - 管理员ID: {admin.id}, 角色: {admin.role}")
                # 设置全局变量
                g.admin = admin
                g.admin_user_id = admin.id
                g.admin_role = admin.role
                return True
        except Exception as e:
            self.logger.error(f"数据库查询失败: {e}")
        
        # 2. 备用：从配置文件验证
        if wallet_address in self.admin_addresses:
            self.logger.info(f"配置文件验证成功: {wallet_address}")
            return True
            
        self.logger.warning(f"管理员验证失败: {wallet_address}")
        return False
    
    def get_admin_info(self, wallet_address: str) -> dict:
        """获取管理员信息"""
        if not wallet_address:
            return None
            
        # 1. 优先从数据库获取
        try:
            admin = self._query_admin_from_database(wallet_address)
            if admin:
                return {
                    'id': admin.id,
                    'wallet_address': admin.wallet_address,
                    'username': admin.username or 'Admin',
                    'role': admin.role,
                    'permissions': admin.permissions,
                    'is_admin': True,
                    'source': 'database'
                }
        except Exception as e:
            self.logger.error(f"从数据库获取管理员信息失败: {e}")
        
        # 2. 备用：从配置文件获取
        admin_config = current_app.config.get('ADMIN_CONFIG', {})
        normalized_address = self._normalize_address(wallet_address)
        
        for config_addr, info in admin_config.items():
            if self._normalize_address(config_addr) == normalized_address:
                return {
                    'wallet_address': wallet_address,
                    'username': info.get('name', 'Admin'),
                    'role': info.get('role', 'admin'),
                    'permissions': info.get('permissions', []),
                    'is_admin': True,
                    'source': 'config'
                }
        
        return None
    
    def _query_admin_from_database(self, wallet_address: str) -> AdminUser:
        """从数据库查询管理员"""
        # 区分以太坊和Solana地址的查询方式
        if wallet_address.startswith('0x'):
            # 以太坊地址：不区分大小写
            admin = AdminUser.query.filter(
                func.lower(AdminUser.wallet_address) == wallet_address.lower()
            ).first()
        else:
            # Solana地址：区分大小写
            admin = AdminUser.query.filter(
                AdminUser.wallet_address == wallet_address
            ).first()
        
        return admin
    
    def _load_admin_addresses(self) -> list:
        """从多个来源加载管理员地址"""
        addresses = []
        
        # 从数据库加载
        try:
            admins = AdminUser.query.all()
            addresses.extend([admin.wallet_address for admin in admins])
            self.logger.info(f"从数据库加载了 {len(admins)} 个管理员地址")
        except Exception as e:
            self.logger.error(f"从数据库加载管理员地址失败: {e}")
        
        # 从配置文件加载
        admin_config = current_app.config.get('ADMIN_CONFIG', {})
        config_addresses = list(admin_config.keys())
        addresses.extend(config_addresses)
        self.logger.info(f"从配置文件加载了 {len(config_addresses)} 个管理员地址")
        
        # 从环境变量加载
        import os
        env_admins = os.environ.get('ADMIN_ADDRESSES', '').split(',')
        env_addresses = [addr.strip() for addr in env_admins if addr.strip()]
        addresses.extend(env_addresses)
        if env_addresses:
            self.logger.info(f"从环境变量加载了 {len(env_addresses)} 个管理员地址")
        
        # 去重并返回
        unique_addresses = list(set(addresses))
        self.logger.info(f"总共加载了 {len(unique_addresses)} 个唯一管理员地址")
        return unique_addresses
    
    def _normalize_address(self, address: str) -> str:
        """标准化地址格式"""
        if not address:
            return ""
        
        # 以太坊地址转小写
        if address.startswith('0x'):
            return address.lower()
        
        # Solana地址保持原样
        return address

# 全局认证服务实例 - 延迟初始化
auth_service = None

def get_auth_service():
    """获取认证服务实例（延迟初始化）"""
    global auth_service
    if auth_service is None:
        auth_service = AuthenticationService()
    return auth_service