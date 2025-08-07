"""
统一数据转换器
提供统一的数据格式转换功能
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class AssetDataConverter:
    """资产数据转换器"""
    
    @staticmethod
    def to_api_format(asset) -> Dict[str, Any]:
        """
        统一的资产数据转换为API格式
        
        Args:
            asset: 资产模型实例
            
        Returns:
            dict: API格式的资产数据
        """
        try:
            # 基础数据
            data = {
                'id': asset.id,
                'name': asset.name or '',
                'description': asset.description or '',
                'token_symbol': asset.token_symbol or '',
                'token_price': float(asset.token_price) if asset.token_price else 0.0,
                'token_supply': asset.token_supply or 0,
                'remaining_supply': asset.remaining_supply or asset.token_supply or 0,
                'creator_address': asset.creator_address or '',
                'owner_address': asset.owner_address or '',
                'token_address': asset.token_address or '',
                'status': asset.status or 'draft',
                'asset_type': asset.asset_type or 'real_estate',
                'created_at': asset.created_at.isoformat() if asset.created_at else None,
                'updated_at': asset.updated_at.isoformat() if asset.updated_at else None,
            }
            
            # 处理图片数据
            if hasattr(asset, 'images') and asset.images:
                if isinstance(asset.images, str):
                    try:
                        data['images'] = json.loads(asset.images)
                    except json.JSONDecodeError:
                        data['images'] = []
                elif isinstance(asset.images, list):
                    data['images'] = asset.images
                else:
                    data['images'] = []
            else:
                data['images'] = []
            
            # 处理文档数据
            if hasattr(asset, 'documents') and asset.documents:
                if isinstance(asset.documents, str):
                    try:
                        data['documents'] = json.loads(asset.documents)
                    except json.JSONDecodeError:
                        data['documents'] = []
                elif isinstance(asset.documents, list):
                    data['documents'] = asset.documents
                else:
                    data['documents'] = []
            else:
                data['documents'] = []
            
            # 计算衍生数据
            data['sold_supply'] = data['token_supply'] - data['remaining_supply']
            data['sold_percentage'] = (data['sold_supply'] / data['token_supply'] * 100) if data['token_supply'] > 0 else 0
            data['market_cap'] = data['token_supply'] * data['token_price']
            data['remaining_value'] = data['remaining_supply'] * data['token_price']
            
            # 状态文本映射
            status_map = {
                'draft': '草稿',
                'pending': '待审核',
                'approved': '已批准',
                'deployed': '已部署',
                'active': '活跃',
                'paused': '暂停',
                'completed': '已完成',
                'cancelled': '已取消'
            }
            data['status_text'] = status_map.get(data['status'], '未知')
            
            # 资产类型文本映射
            type_map = {
                'real_estate': '房地产',
                'commodity': '商品',
                'art': '艺术品',
                'collectible': '收藏品',
                'other': '其他'
            }
            data['type_text'] = type_map.get(data['asset_type'], '未知')
            
            return data
            
        except Exception as e:
            logger.error(f"资产数据转换失败: {e}")
            # 返回基础数据结构，避免完全失败
            return {
                'id': getattr(asset, 'id', None),
                'name': getattr(asset, 'name', ''),
                'description': getattr(asset, 'description', ''),
                'token_symbol': getattr(asset, 'token_symbol', ''),
                'token_price': 0.0,
                'token_supply': 0,
                'remaining_supply': 0,
                'images': [],
                'documents': [],
                'status': 'draft',
                'status_text': '草稿',
                'asset_type': 'real_estate',
                'type_text': '房地产',
                'created_at': None,
                'updated_at': None
            }
    
    @staticmethod
    def to_admin_format(asset) -> Dict[str, Any]:
        """
        转换为管理后台格式
        
        Args:
            asset: 资产模型实例
            
        Returns:
            dict: 管理后台格式的资产数据
        """
        data = AssetDataConverter.to_api_format(asset)
        
        # 添加管理后台特有字段
        data.update({
            'creator_address': asset.creator_address or '',
            'owner_address': asset.owner_address or '',
            'token_address': asset.token_address or '',
            'contract_deployed': bool(asset.token_address),
            'deployment_tx_hash': getattr(asset, 'deployment_tx_hash', ''),
            'deployment_block': getattr(asset, 'deployment_block', ''),
            'gas_used': getattr(asset, 'gas_used', 0),
            'deleted_at': asset.deleted_at.isoformat() if getattr(asset, 'deleted_at', None) else None,
        })
        
        return data
    
    @staticmethod
    def to_trading_format(asset) -> Dict[str, Any]:
        """
        转换为交易页面格式
        
        Args:
            asset: 资产模型实例
            
        Returns:
            dict: 交易页面格式的资产数据
        """
        data = AssetDataConverter.to_api_format(asset)
        
        # 只保留交易相关的必要字段
        trading_data = {
            'id': data['id'],
            'name': data['name'],
            'token_symbol': data['token_symbol'],
            'token_price': data['token_price'],
            'remaining_supply': data['remaining_supply'],
            'images': data['images'][:1] if data['images'] else [],  # 只保留第一张图片
            'status': data['status'],
            'market_cap': data['market_cap'],
            'remaining_value': data['remaining_value']
        }
        
        return trading_data


class TradeDataConverter:
    """交易数据转换器"""
    
    @staticmethod
    def to_api_format(trade) -> Dict[str, Any]:
        """
        统一的交易数据转换为API格式
        
        Args:
            trade: 交易模型实例
            
        Returns:
            dict: API格式的交易数据
        """
        try:
            data = {
                'id': trade.id,
                'asset_id': trade.asset_id,
                'trader_address': trade.trader_address or '',
                'amount': trade.amount or 0,
                'price': float(trade.price) if trade.price else 0.0,
                'total': float(trade.total) if trade.total else 0.0,
                'type': trade.type or 'buy',
                'status': trade.status or 'pending',
                'tx_hash': trade.tx_hash or '',
                'block_number': getattr(trade, 'block_number', 0),
                'gas_used': trade.gas_used or 0,
                'created_at': trade.created_at.isoformat() if trade.created_at else None,
                'updated_at': trade.status_updated_at.isoformat() if hasattr(trade, 'status_updated_at') and trade.status_updated_at else (trade.created_at.isoformat() if trade.created_at else None),
            }
            
            # 状态文本映射
            status_map = {
                'pending': '待处理',
                'processing': '处理中',
                'completed': '已完成',
                'failed': '失败',
                'cancelled': '已取消'
            }
            data['status_text'] = status_map.get(data['status'], '未知')
            
            # 交易类型文本映射
            type_map = {
                'buy': '购买',
                'sell': '出售'
            }
            data['type_text'] = type_map.get(data['type'], '未知')
            
            # 添加资产信息（如果有关联）
            if hasattr(trade, 'asset') and trade.asset:
                data['asset_name'] = trade.asset.name
                data['asset_symbol'] = trade.asset.token_symbol
            
            return data
            
        except Exception as e:
            logger.error(f"交易数据转换失败: {e}")
            # 即使转换失败，也要提供基本的时间信息
            created_at = None
            updated_at = None
            try:
                if hasattr(trade, 'created_at') and trade.created_at:
                    created_at = trade.created_at.isoformat()
                if hasattr(trade, 'status_updated_at') and trade.status_updated_at:
                    updated_at = trade.status_updated_at.isoformat()
                elif created_at:
                    updated_at = created_at
            except:
                pass
                
            return {
                'id': getattr(trade, 'id', None),
                'asset_id': getattr(trade, 'asset_id', None),
                'trader_address': getattr(trade, 'trader_address', ''),
                'amount': getattr(trade, 'amount', 0),
                'price': float(getattr(trade, 'price', 0)),
                'total': float(getattr(trade, 'total', 0)),
                'type': getattr(trade, 'type', 'buy'),
                'status': getattr(trade, 'status', 'pending'),
                'tx_hash': getattr(trade, 'tx_hash', ''),
                'created_at': created_at,
                'updated_at': updated_at
            }


class UserDataConverter:
    """用户数据转换器"""
    
    @staticmethod
    def to_api_format(user) -> Dict[str, Any]:
        """
        统一的用户数据转换为API格式
        
        Args:
            user: 用户模型实例
            
        Returns:
            dict: API格式的用户数据
        """
        try:
            data = {
                'id': user.id,
                'username': user.username or '',
                'email': user.email or '',
                'eth_address': user.eth_address or '',
                'solana_address': getattr(user, 'solana_address', '') or '',
                'wallet_type': getattr(user, 'wallet_type', 'ethereum'),
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            }
            
            # 确定主要钱包地址
            if data['wallet_type'] == 'solana' and data['solana_address']:
                data['primary_address'] = data['solana_address']
            else:
                data['primary_address'] = data['eth_address']
            
            return data
            
        except Exception as e:
            logger.error(f"用户数据转换失败: {e}")
            return {
                'id': getattr(user, 'id', None),
                'username': '',
                'email': '',
                'eth_address': '',
                'solana_address': '',
                'wallet_type': 'ethereum',
                'primary_address': '',
                'created_at': None,
                'updated_at': None
            }


class CommissionDataConverter:
    """佣金数据转换器"""
    
    @staticmethod
    def to_api_format(commission) -> Dict[str, Any]:
        """
        统一的佣金数据转换为API格式
        
        Args:
            commission: 佣金模型实例
            
        Returns:
            dict: API格式的佣金数据
        """
        try:
            data = {
                'id': commission.id,
                'transaction_id': getattr(commission, 'transaction_id', None),
                'referrer_address': commission.referrer_address or '',
                'referred_address': getattr(commission, 'referred_address', '') or '',
                'commission_amount': float(commission.commission_amount) if commission.commission_amount else 0.0,
                'commission_rate': float(commission.commission_rate) if commission.commission_rate else 0.0,
                'level': getattr(commission, 'level', 1),
                'status': commission.status or 'pending',
                'created_at': commission.created_at.isoformat() if commission.created_at else None,
                'updated_at': commission.updated_at.isoformat() if commission.updated_at else None,
            }
            
            # 状态文本映射
            status_map = {
                'pending': '待发放',
                'paid': '已发放',
                'cancelled': '已取消'
            }
            data['status_text'] = status_map.get(data['status'], '未知')
            
            return data
            
        except Exception as e:
            logger.error(f"佣金数据转换失败: {e}")
            return {
                'id': getattr(commission, 'id', None),
                'referrer_address': '',
                'commission_amount': 0.0,
                'commission_rate': 0.0,
                'level': 1,
                'status': 'pending',
                'created_at': None,
                'updated_at': None
            }


class DataConverter:
    """通用数据转换器"""
    
    @staticmethod
    def safe_decimal_to_float(value: Union[Decimal, str, int, float, None]) -> float:
        """
        安全地将Decimal转换为float
        
        Args:
            value: 要转换的值
            
        Returns:
            float: 转换后的浮点数
        """
        if value is None:
            return 0.0
        
        try:
            if isinstance(value, Decimal):
                return float(value)
            elif isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                return float(Decimal(value))
            else:
                return 0.0
        except (ValueError, InvalidOperation):
            return 0.0
    
    @staticmethod
    def safe_datetime_to_iso(dt: Optional[datetime]) -> Optional[str]:
        """
        安全地将datetime转换为ISO格式字符串
        
        Args:
            dt: datetime对象
            
        Returns:
            str: ISO格式的时间字符串，如果输入为None则返回None
        """
        if dt is None:
            return None
        
        try:
            return dt.isoformat()
        except Exception:
            return None
    
    @staticmethod
    def safe_json_loads(json_str: Optional[str], default: Any = None) -> Any:
        """
        安全地解析JSON字符串
        
        Args:
            json_str: JSON字符串
            default: 解析失败时的默认值
            
        Returns:
            解析后的对象或默认值
        """
        if not json_str:
            return default
        
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return default
    
    @staticmethod
    def safe_json_dumps(obj: Any, default: str = '{}') -> str:
        """
        安全地序列化对象为JSON字符串
        
        Args:
            obj: 要序列化的对象
            default: 序列化失败时的默认值
            
        Returns:
            JSON字符串
        """
        try:
            return json.dumps(obj, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def paginate_data(data: List[Dict], page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        对数据进行分页处理
        
        Args:
            data: 要分页的数据列表
            page: 页码（从1开始）
            per_page: 每页数量
            
        Returns:
            dict: 包含分页信息的数据
        """
        total = len(data)
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'data': data[start:end],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_prev': page > 1,
                'has_next': end < total
            }
        }