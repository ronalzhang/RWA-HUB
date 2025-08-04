#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
系统健康检查服务
实现系统健康检查端点、数据库连接状态检查、区块链网络连接监控和关键功能可用性检查
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import psutil
import requests

from app.extensions import db
from sqlalchemy import text

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """健康检查结果"""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = None
    response_time: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}

class HealthCheckService:
    """健康检查服务"""
    
    def __init__(self):
        self.checks = {}
        self.last_check_results = {}
        self.check_history = {}
        
        # 注册默认检查项
        self._register_default_checks()
    
    def _register_default_checks(self):
        """注册默认的健康检查项"""
        self.register_check("database", self._check_database_health)
        self.register_check("redis_cache", self._check_redis_health)
        self.register_check("system_resources", self._check_system_resources)
        self.register_check("solana_network", self._check_solana_network)
        self.register_check("api_endpoints", self._check_api_endpoints)
        self.register_check("background_tasks", self._check_background_tasks)
    
    def register_check(self, name: str, check_func):
        """注册健康检查函数"""
        self.checks[name] = check_func
        logger.debug(f"注册健康检查: {name}")
    
    def run_check(self, check_name: str) -> HealthCheckResult:
        """运行单个健康检查"""
        if check_name not in self.checks:
            return HealthCheckResult(
                name=check_name,
                status=HealthStatus.UNKNOWN,
                message=f"未知的检查项: {check_name}"
            )
        
        start_time = time.time()
        
        try:
            result = self.checks[check_name]()
            result.response_time = time.time() - start_time
            
            # 记录检查结果
            self.last_check_results[check_name] = result
            
            # 记录历史（保留最近100次）
            if check_name not in self.check_history:
                self.check_history[check_name] = []
            
            self.check_history[check_name].append(result)
            if len(self.check_history[check_name]) > 100:
                self.check_history[check_name] = self.check_history[check_name][-100:]
            
            return result
            
        except Exception as e:
            error_result = HealthCheckResult(
                name=check_name,
                status=HealthStatus.CRITICAL,
                message=f"检查执行失败: {str(e)}",
                response_time=time.time() - start_time
            )
            
            self.last_check_results[check_name] = error_result
            logger.error(f"健康检查 {check_name} 失败: {e}")
            
            return error_result
    
    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """运行所有健康检查"""
        results = {}
        
        for check_name in self.checks.keys():
            results[check_name] = self.run_check(check_name)
        
        return results
    
    def get_overall_health(self) -> Tuple[HealthStatus, Dict[str, Any]]:
        """获取系统整体健康状态"""
        results = self.run_all_checks()
        
        # 统计各状态数量
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.WARNING: 0,
            HealthStatus.CRITICAL: 0,
            HealthStatus.UNKNOWN: 0
        }
        
        for result in results.values():
            status_counts[result.status] += 1
        
        # 确定整体状态
        if status_counts[HealthStatus.CRITICAL] > 0:
            overall_status = HealthStatus.CRITICAL
        elif status_counts[HealthStatus.WARNING] > 0:
            overall_status = HealthStatus.WARNING
        elif status_counts[HealthStatus.UNKNOWN] > 0:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY
        
        summary = {
            'overall_status': overall_status.value,
            'total_checks': len(results),
            'healthy': status_counts[HealthStatus.HEALTHY],
            'warning': status_counts[HealthStatus.WARNING],
            'critical': status_counts[HealthStatus.CRITICAL],
            'unknown': status_counts[HealthStatus.UNKNOWN],
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {name: {
                'status': result.status.value,
                'message': result.message,
                'response_time': result.response_time,
                'details': result.details
            } for name, result in results.items()}
        }
        
        return overall_status, summary
    
    def _check_database_health(self) -> HealthCheckResult:
        """检查数据库健康状态"""
        try:
            start_time = time.time()
            
            # 测试基本连接
            db.session.execute(text("SELECT 1"))
            
            # 检查连接池状态
            engine = db.engine
            pool = engine.pool
            
            pool_info = {
                'pool_size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalid': pool.invalid()
            }
            
            # 检查数据库版本和基本信息
            version_result = db.session.execute(text("SELECT version()")).fetchone()
            db_version = version_result[0] if version_result else "Unknown"
            
            # 检查活跃连接数
            active_connections_result = db.session.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            ).fetchone()
            active_connections = active_connections_result[0] if active_connections_result else 0
            
            query_time = time.time() - start_time
            
            # 判断健康状态
            if query_time > 5.0:
                status = HealthStatus.CRITICAL
                message = f"数据库响应缓慢: {query_time:.2f}s"
            elif query_time > 2.0:
                status = HealthStatus.WARNING
                message = f"数据库响应较慢: {query_time:.2f}s"
            elif pool_info['checked_out'] > pool_info['pool_size'] * 0.8:
                status = HealthStatus.WARNING
                message = "数据库连接池使用率较高"
            else:
                status = HealthStatus.HEALTHY
                message = "数据库连接正常"
            
            return HealthCheckResult(
                name="database",
                status=status,
                message=message,
                details={
                    'query_time': query_time,
                    'pool_info': pool_info,
                    'db_version': db_version,
                    'active_connections': active_connections
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="database",
                status=HealthStatus.CRITICAL,
                message=f"数据库连接失败: {str(e)}"
            )
    
    def _check_redis_health(self) -> HealthCheckResult:
        """检查Redis缓存健康状态"""
        try:
            from app.services.cache_service import get_cache
            
            cache = get_cache()
            
            # 测试缓存读写
            test_key = "health_check_test"
            test_value = f"test_{int(time.time())}"
            
            start_time = time.time()
            
            # 写入测试
            cache.set(test_key, test_value, 10)
            
            # 读取测试
            retrieved_value = cache.get(test_key)
            
            # 清理测试数据
            cache.delete(test_key)
            
            response_time = time.time() - start_time
            
            # 获取缓存统计
            cache_stats = cache.get_stats()
            
            if retrieved_value != test_value:
                return HealthCheckResult(
                    name="redis_cache",
                    status=HealthStatus.CRITICAL,
                    message="缓存读写测试失败",
                    details={'cache_stats': cache_stats}
                )
            
            if response_time > 1.0:
                status = HealthStatus.WARNING
                message = f"缓存响应较慢: {response_time:.2f}s"
            else:
                status = HealthStatus.HEALTHY
                message = "缓存服务正常"
            
            return HealthCheckResult(
                name="redis_cache",
                status=status,
                message=message,
                details={
                    'response_time': response_time,
                    'cache_stats': cache_stats
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="redis_cache",
                status=HealthStatus.WARNING,
                message=f"缓存服务异常: {str(e)}"
            )
    
    def _check_system_resources(self) -> HealthCheckResult:
        """检查系统资源使用情况"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 网络连接数
            try:
                network_connections = len(psutil.net_connections())
            except:
                network_connections = 0
            
            # 进程数
            process_count = len(psutil.pids())
            
            details = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk_percent,
                'disk_free_gb': disk.free / (1024**3),
                'network_connections': network_connections,
                'process_count': process_count
            }
            
            # 判断健康状态
            if cpu_percent > 90 or memory_percent > 95 or disk_percent > 95:
                status = HealthStatus.CRITICAL
                message = "系统资源严重不足"
            elif cpu_percent > 80 or memory_percent > 85 or disk_percent > 90:
                status = HealthStatus.WARNING
                message = "系统资源使用率较高"
            else:
                status = HealthStatus.HEALTHY
                message = "系统资源使用正常"
            
            return HealthCheckResult(
                name="system_resources",
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="system_resources",
                status=HealthStatus.UNKNOWN,
                message=f"无法获取系统资源信息: {str(e)}"
            )
    
    def _check_solana_network(self) -> HealthCheckResult:
        """检查Solana网络连接"""
        try:
            from app.config import Config
            
            rpc_url = Config.SOLANA_RPC_URL
            
            start_time = time.time()
            
            # 测试RPC连接
            response = requests.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth"
                },
                timeout=10
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                if 'result' in result and result['result'] == 'ok':
                    status = HealthStatus.HEALTHY
                    message = "Solana网络连接正常"
                else:
                    status = HealthStatus.WARNING
                    message = "Solana网络状态异常"
                
                # 获取更多网络信息
                try:
                    slot_response = requests.post(
                        rpc_url,
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "getSlot"
                        },
                        timeout=5
                    )
                    
                    current_slot = None
                    if slot_response.status_code == 200:
                        slot_result = slot_response.json()
                        current_slot = slot_result.get('result')
                    
                except:
                    current_slot = None
                
                return HealthCheckResult(
                    name="solana_network",
                    status=status,
                    message=message,
                    details={
                        'rpc_url': rpc_url,
                        'response_time': response_time,
                        'current_slot': current_slot,
                        'network_status': result.get('result')
                    }
                )
            else:
                return HealthCheckResult(
                    name="solana_network",
                    status=HealthStatus.CRITICAL,
                    message=f"Solana RPC请求失败: HTTP {response.status_code}",
                    details={'rpc_url': rpc_url, 'response_time': response_time}
                )
                
        except requests.RequestException as e:
            return HealthCheckResult(
                name="solana_network",
                status=HealthStatus.CRITICAL,
                message=f"Solana网络连接失败: {str(e)}"
            )
        except Exception as e:
            return HealthCheckResult(
                name="solana_network",
                status=HealthStatus.UNKNOWN,
                message=f"Solana网络检查异常: {str(e)}"
            )
    
    def _check_api_endpoints(self) -> HealthCheckResult:
        """检查关键API端点"""
        try:
            from flask import current_app
            
            # 测试本地API端点
            test_endpoints = [
                '/api/assets/list',
                '/api/health',
            ]
            
            endpoint_results = {}
            total_response_time = 0
            failed_endpoints = 0
            
            for endpoint in test_endpoints:
                try:
                    with current_app.test_client() as client:
                        start_time = time.time()
                        response = client.get(endpoint)
                        response_time = time.time() - start_time
                        
                        endpoint_results[endpoint] = {
                            'status_code': response.status_code,
                            'response_time': response_time,
                            'success': response.status_code < 400
                        }
                        
                        total_response_time += response_time
                        
                        if response.status_code >= 400:
                            failed_endpoints += 1
                            
                except Exception as e:
                    endpoint_results[endpoint] = {
                        'error': str(e),
                        'success': False
                    }
                    failed_endpoints += 1
            
            avg_response_time = total_response_time / len(test_endpoints) if test_endpoints else 0
            
            # 判断健康状态
            if failed_endpoints > 0:
                status = HealthStatus.CRITICAL
                message = f"{failed_endpoints}/{len(test_endpoints)} API端点异常"
            elif avg_response_time > 2.0:
                status = HealthStatus.WARNING
                message = f"API响应较慢: {avg_response_time:.2f}s"
            else:
                status = HealthStatus.HEALTHY
                message = "API端点正常"
            
            return HealthCheckResult(
                name="api_endpoints",
                status=status,
                message=message,
                details={
                    'endpoints': endpoint_results,
                    'avg_response_time': avg_response_time,
                    'failed_count': failed_endpoints,
                    'total_count': len(test_endpoints)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="api_endpoints",
                status=HealthStatus.UNKNOWN,
                message=f"API端点检查异常: {str(e)}"
            )
    
    def _check_background_tasks(self) -> HealthCheckResult:
        """检查后台任务处理器"""
        try:
            from app.services.async_task_processor import get_task_processor
            
            processor = get_task_processor()
            stats = processor.get_queue_stats()
            
            # 判断健康状态
            queue_usage = stats['queue_size'] / stats['max_queue_size'] if stats['max_queue_size'] > 0 else 0
            
            if not stats['running']:
                status = HealthStatus.CRITICAL
                message = "后台任务处理器未运行"
            elif queue_usage > 0.9:
                status = HealthStatus.CRITICAL
                message = "任务队列接近满载"
            elif queue_usage > 0.7:
                status = HealthStatus.WARNING
                message = "任务队列使用率较高"
            else:
                status = HealthStatus.HEALTHY
                message = "后台任务处理正常"
            
            return HealthCheckResult(
                name="background_tasks",
                status=status,
                message=message,
                details=stats
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="background_tasks",
                status=HealthStatus.WARNING,
                message=f"后台任务检查异常: {str(e)}"
            )
    
    def get_check_history(self, check_name: str, limit: int = 50) -> List[HealthCheckResult]:
        """获取检查历史"""
        history = self.check_history.get(check_name, [])
        return history[-limit:] if limit else history
    
    def get_uptime_stats(self, check_name: str, hours: int = 24) -> Dict[str, Any]:
        """获取可用性统计"""
        history = self.get_check_history(check_name, limit=1000)
        
        if not history:
            return {}
        
        # 过滤指定时间范围内的记录
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_history = [h for h in history if h.timestamp >= cutoff_time]
        
        if not recent_history:
            return {}
        
        total_checks = len(recent_history)
        healthy_checks = len([h for h in recent_history if h.status == HealthStatus.HEALTHY])
        warning_checks = len([h for h in recent_history if h.status == HealthStatus.WARNING])
        critical_checks = len([h for h in recent_history if h.status == HealthStatus.CRITICAL])
        
        uptime_percentage = (healthy_checks / total_checks) * 100 if total_checks > 0 else 0
        
        # 计算平均响应时间
        response_times = [h.response_time for h in recent_history if h.response_time > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'check_name': check_name,
            'time_range_hours': hours,
            'total_checks': total_checks,
            'uptime_percentage': uptime_percentage,
            'healthy_checks': healthy_checks,
            'warning_checks': warning_checks,
            'critical_checks': critical_checks,
            'avg_response_time': avg_response_time,
            'last_check': recent_history[-1].timestamp.isoformat() if recent_history else None
        }

# 全局健康检查服务实例
_health_check_instance = None

def get_health_check_service() -> HealthCheckService:
    """获取全局健康检查服务实例"""
    global _health_check_instance
    if _health_check_instance is None:
        _health_check_instance = HealthCheckService()
    return _health_check_instance