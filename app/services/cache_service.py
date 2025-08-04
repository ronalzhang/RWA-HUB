#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
缓存服务
实现Redis缓存机制，提升系统性能
"""

import json
import pickle
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Union, Dict, List
from functools import wraps
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)

class CacheService:
    """缓存服务类"""
    
    def __init__(self, redis_url: str = 'redis://localhost:6379/0', 
                 default_timeout: int = 300):
        self.default_timeout = default_timeout
        self.redis_client = None
        self._fallback_cache = {}  # 内存回退缓存
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                # 测试连接
                self.redis_client.ping()
                logger.info("Redis缓存服务已启动")
            except Exception as e:
                logger.warning(f"Redis连接失败，使用内存缓存: {e}")
                self.redis_client = None
        else:
            logger.warning("Redis未安装，使用内存缓存")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value is not None:
                    return pickle.loads(value)
            else:
                # 使用内存缓存
                cache_item = self._fallback_cache.get(key)
                if cache_item and cache_item['expires_at'] > datetime.utcnow():
                    return cache_item['value']
                elif cache_item:
                    # 过期了，删除
                    del self._fallback_cache[key]
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            timeout = timeout or self.default_timeout
            
            if self.redis_client:
                serialized_value = pickle.dumps(value)
                return self.redis_client.setex(key, timeout, serialized_value)
            else:
                # 使用内存缓存
                expires_at = datetime.utcnow() + timedelta(seconds=timeout)
                self._fallback_cache[key] = {
                    'value': value,
                    'expires_at': expires_at
                }
                
                # 清理过期的内存缓存
                self._cleanup_memory_cache()
                return True
                
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                if key in self._fallback_cache:
                    del self._fallback_cache[key]
                    return True
                return False
                
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            if self.redis_client:
                return bool(self.redis_client.exists(key))
            else:
                cache_item = self._fallback_cache.get(key)
                return cache_item is not None and cache_item['expires_at'] > datetime.utcnow()
                
        except Exception as e:
            logger.error(f"检查缓存存在性失败 {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的缓存"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # 内存缓存模式匹配
                import fnmatch
                keys_to_delete = [key for key in self._fallback_cache.keys() 
                                if fnmatch.fnmatch(key, pattern)]
                for key in keys_to_delete:
                    del self._fallback_cache[key]
                return len(keys_to_delete)
                
        except Exception as e:
            logger.error(f"清除模式缓存失败 {pattern}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            if self.redis_client:
                info = self.redis_client.info()
                return {
                    'type': 'redis',
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory': info.get('used_memory', 0),
                    'used_memory_human': info.get('used_memory_human', '0B'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0)
                }
            else:
                return {
                    'type': 'memory',
                    'total_keys': len(self._fallback_cache),
                    'memory_usage': f"{len(str(self._fallback_cache))} bytes (approx)"
                }
                
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {'type': 'error', 'message': str(e)}
    
    def _cleanup_memory_cache(self):
        """清理过期的内存缓存"""
        try:
            current_time = datetime.utcnow()
            expired_keys = [key for key, item in self._fallback_cache.items() 
                          if item['expires_at'] <= current_time]
            
            for key in expired_keys:
                del self._fallback_cache[key]
                
            # 如果内存缓存过大，删除最老的条目
            if len(self._fallback_cache) > 1000:
                # 按过期时间排序，删除最老的100个
                sorted_items = sorted(self._fallback_cache.items(), 
                                    key=lambda x: x[1]['expires_at'])
                for key, _ in sorted_items[:100]:
                    del self._fallback_cache[key]
                    
        except Exception as e:
            logger.error(f"清理内存缓存失败: {e}")

# 全局缓存实例
_cache_instance = None

def get_cache() -> CacheService:
    """获取全局缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance

def cache_result(timeout: int = 300, key_prefix: str = ''):
    """缓存函数结果的装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成缓存键
            cache_key = _generate_cache_key(f.__name__, args, kwargs, key_prefix)
            
            # 尝试从缓存获取
            cache = get_cache()
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
            
            # 执行函数并缓存结果
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            logger.debug(f"缓存设置: {cache_key}")
            
            return result
        
        return decorated_function
    return decorator

def cache_model_query(model_name: str, timeout: int = 300):
    """缓存数据库模型查询的装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成缓存键
            cache_key = f"model:{model_name}:{_generate_cache_key(f.__name__, args, kwargs)}"
            
            # 尝试从缓存获取
            cache = get_cache()
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                logger.debug(f"模型查询缓存命中: {cache_key}")
                return cached_result
            
            # 执行查询并缓存结果
            result = f(*args, **kwargs)
            
            # 只缓存非空结果
            if result is not None:
                cache.set(cache_key, result, timeout)
                logger.debug(f"模型查询缓存设置: {cache_key}")
            
            return result
        
        return decorated_function
    return decorator

def invalidate_model_cache(model_name: str, pattern: str = '*'):
    """使模型缓存失效"""
    cache = get_cache()
    cache_pattern = f"model:{model_name}:{pattern}"
    deleted_count = cache.clear_pattern(cache_pattern)
    logger.info(f"清除模型缓存: {cache_pattern}, 删除 {deleted_count} 个键")
    return deleted_count

def _generate_cache_key(func_name: str, args: tuple, kwargs: dict, prefix: str = '') -> str:
    """生成缓存键"""
    # 创建参数的哈希值
    key_data = {
        'func': func_name,
        'args': str(args),
        'kwargs': str(sorted(kwargs.items()))
    }
    
    key_string = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    if prefix:
        return f"{prefix}:{key_hash}"
    else:
        return f"func:{func_name}:{key_hash}"

class CacheManager:
    """缓存管理器 - 提供高级缓存操作"""
    
    def __init__(self, cache_service: CacheService = None):
        self.cache = cache_service or get_cache()
    
    def cache_asset_data(self, asset_id: int, data: Dict, timeout: int = 600):
        """缓存资产数据"""
        key = f"asset:{asset_id}"
        return self.cache.set(key, data, timeout)
    
    def get_asset_data(self, asset_id: int) -> Optional[Dict]:
        """获取缓存的资产数据"""
        key = f"asset:{asset_id}"
        return self.cache.get(key)
    
    def invalidate_asset_cache(self, asset_id: int):
        """使资产缓存失效"""
        key = f"asset:{asset_id}"
        self.cache.delete(key)
        # 同时清除相关的列表缓存
        self.cache.clear_pattern("assets:list:*")
    
    def cache_user_data(self, user_address: str, data: Dict, timeout: int = 300):
        """缓存用户数据"""
        key = f"user:{user_address}"
        return self.cache.set(key, data, timeout)
    
    def get_user_data(self, user_address: str) -> Optional[Dict]:
        """获取缓存的用户数据"""
        key = f"user:{user_address}"
        return self.cache.get(key)
    
    def cache_trade_data(self, trade_id: int, data: Dict, timeout: int = 180):
        """缓存交易数据"""
        key = f"trade:{trade_id}"
        return self.cache.set(key, data, timeout)
    
    def get_trade_data(self, trade_id: int) -> Optional[Dict]:
        """获取缓存的交易数据"""
        key = f"trade:{trade_id}"
        return self.cache.get(key)
    
    def cache_api_response(self, endpoint: str, params: Dict, response: Any, timeout: int = 120):
        """缓存API响应"""
        params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
        key = f"api:{endpoint}:{params_hash}"
        return self.cache.set(key, response, timeout)
    
    def get_cached_api_response(self, endpoint: str, params: Dict) -> Optional[Any]:
        """获取缓存的API响应"""
        params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
        key = f"api:{endpoint}:{params_hash}"
        return self.cache.get(key)
    
    def warm_up_cache(self):
        """预热缓存 - 预加载常用数据"""
        try:
            from app.models.asset import Asset
            from app.models.user import User
            
            # 预加载热门资产
            logger.info("开始预热资产缓存...")
            # 这里可以添加预加载逻辑
            
            logger.info("缓存预热完成")
            
        except Exception as e:
            logger.error(f"缓存预热失败: {e}")

# 全局缓存管理器实例
_cache_manager_instance = None

def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager_instance
    if _cache_manager_instance is None:
        _cache_manager_instance = CacheManager()
    return _cache_manager_instance