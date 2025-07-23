from flask import current_app, session, request, g
from app.models.admin import AdminUser
import logging

class AuthenticationService:
    """统一的认证服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def verify_admin_wallet(self, wallet_address: str) -> bool:
        """验证管理员钱包地址"""
        if not wallet_address:
            return False
            
        # 标准化地址格式
        normalized_address = self._normalize_address(wallet_address)
        
        # 1. 优先检查数据库中的管理员记录
        try:
            admin = AdminUser.query.filter_by(wallet_address=normalized_address).first()
            if admin and admin.role in ['admin', 'super_admin']:
                self.logger.info(f"从数据库验证管理员成功: {normalized_address}")
                return True
        except Exception as e:
            self.logger.error(f"数据库验证管理员时出错: {e}")
        
        # 2. 备用：检查配置文件
        admin_config = current_app.config.get('ADMIN_CONFIG', {})
        for admin_addr in admin_config.keys():
            if self._normalize_address(admin_addr) == normalized_address:
                self.logger.info(f"从配置文件验证管理员成功: {normalized_address}")
                return True
        
        # 3. 兼容性：检查旧的ADMIN_ADDRESSES配置
        admin_addresses = current_app.config.get('ADMIN_ADDRESSES', [])
        for admin_addr in admin_addresses:
            if self._normalize_address(admin_addr) == normalized_address:
                self.logger.info(f"从旧配置验证管理员成功: {normalized_address}")
                return True
        
        self.logger.warning(f"管理员验证失败: {normalized_address}")
        return False
    
    def get_admin_info(self, wallet_address: str) -> dict:
        """获取管理员信息"""
        if not self.verify_admin_wallet(wallet_address):
            return None
            
        normalized_address = self._normalize_address(wallet_address)
        
        # 优先从数据库获取
        try:
            admin = AdminUser.query.filter_by(wallet_address=normalized_address).first()
            if admin:
                import json
                return {
                    'wallet_address': admin.wallet_address,
                    'username': admin.username,
                    'role': admin.role,
                    'permissions': json.loads(admin.permissions) if admin.permissions else [],
                    'is_super_admin': admin.role == 'super_admin'
                }
        except Exception as e:
            self.logger.error(f"获取管理员信息时出错: {e}")
        
        # 备用：从配置文件获取
        admin_config = current_app.config.get('ADMIN_CONFIG', {})
        for admin_addr, info in admin_config.items():
            if self._normalize_address(admin_addr) == normalized_address:
                return {
                    'wallet_address': admin_addr,
                    'username': info.get('name', '管理员'),
                    'role': info.get('role', 'admin'),
                    'permissions': info.get('permissions', []),
                    'is_super_admin': info.get('role') == 'super_admin'
                }
        
        return None
    
    def _normalize_address(self, address: str) -> str:
        """标准化地址格式"""
        if not address:
            return ''
        
        # 以太坊地址转小写
        if address.startswith('0x'):
            return address.lower()
        
        # Solana地址保持原样
        return address
    
    def extract_wallet_address(self) -> str:
        """从请求中提取钱包地址"""
        # 按优先级检查各种来源
        sources = [
            ('headers', lambda: request.headers.get('X-Wallet-Address') or request.headers.get('X-Eth-Address')),
            ('cookies', lambda: request.cookies.get('wallet_address') or request.cookies.get('eth_address')),
            ('args', lambda: request.args.get('wallet_address') or request.args.get('eth_address')),
            ('session', lambda: session.get('wallet_address') or session.get('eth_address')),
        ]
        
        # 如果是POST请求，还要检查请求体
        if request.method == 'POST':
            if request.is_json:
                json_data = request.get_json(silent=True) or {}
                sources.append(('json', lambda: json_data.get('wallet_address') or json_data.get('from_address')))
            elif request.form:
                sources.append(('form', lambda: request.form.get('wallet_address') or request.form.get('eth_address')))
        
        for source_name, getter in sources:
            try:
                address = getter()
                if address:
                    self.logger.debug(f"从 {source_name} 找到钱包地址: {address}")
                    return address
            except Exception as e:
                self.logger.debug(f"从 {source_name} 获取地址时出错: {e}")
        
        return None

# 全局认证服务实例
auth_service = AuthenticationService()
