#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
应用性能监控服务
实现API响应时间跟踪、数据库查询性能监控和系统资源使用监控
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from functools import wraps
import logging
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    endpoint: str
    duration: float
    timestamp: datetime
    status_code: int = 200
    method: str = 'GET'
    user_agent: str = ''
    ip_address: str = ''

@dataclass
class DatabaseMetric:
    """数据库查询指标数据类"""
    query_type: str
    duration: float
    timestamp: datetime
    table_name: str = ''
    rows_affected: int = 0

@dataclass
class SystemResourceMetric:
    """系统资源指标数据类"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    timestamp: datetime
    active_connections: int = 0

class ApplicationMonitor:
    """应用性能监控类"""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.api_metrics = deque(maxlen=max_metrics)
        self.db_metrics = deque(maxlen=max_metrics)
        self.system_metrics = deque(maxlen=max_metrics)
        self.error_counts = defaultdict(int)
        self.alert_thresholds = {
            'api_response_time': 5.0,  # 5秒
            'cpu_usage': 80.0,         # 80%
            'memory_usage': 85.0,      # 85%
            'disk_usage': 90.0,        # 90%
            'error_rate': 10           # 10个错误/分钟
        }
        self._lock = threading.Lock()
        self._start_system_monitoring()
    
    def track_api_performance(self, endpoint: str, duration: float, 
                            status_code: int = 200, method: str = 'GET',
                            user_agent: str = '', ip_address: str = ''):
        """跟踪API性能指标"""
        with self._lock:
            metric = PerformanceMetric(
                endpoint=endpoint,
                duration=duration,
                timestamp=datetime.utcnow(),
                status_code=status_code,
                method=method,
                user_agent=user_agent,
                ip_address=ip_address
            )
            self.api_metrics.append(metric)
            
            # 检查是否需要告警
            if duration > self.alert_thresholds['api_response_time']:
                self._log_performance_alert('API_SLOW_RESPONSE', {
                    'endpoint': endpoint,
                    'duration': duration,
                    'threshold': self.alert_thresholds['api_response_time']
                })
    
    def track_database_performance(self, query_type: str, duration: float,
                                 table_name: str = '', rows_affected: int = 0):
        """跟踪数据库查询性能"""
        with self._lock:
            metric = DatabaseMetric(
                query_type=query_type,
                duration=duration,
                timestamp=datetime.utcnow(),
                table_name=table_name,
                rows_affected=rows_affected
            )
            self.db_metrics.append(metric)
            
            # 记录慢查询
            if duration > 1.0:  # 超过1秒的查询
                logger.warning(f"慢查询检测: {query_type} on {table_name}, 耗时: {duration:.2f}s")
    
    def track_error(self, error_type: str, error_message: str, context: Dict = None):
        """跟踪错误"""
        with self._lock:
            self.error_counts[error_type] += 1
            
            error_log = {
                'type': error_type,
                'message': error_message,
                'context': context or {},
                'timestamp': datetime.utcnow().isoformat(),
                'count': self.error_counts[error_type]
            }
            
            logger.error(f"错误跟踪: {json.dumps(error_log, ensure_ascii=False)}")
            
            # 检查错误率告警
            recent_errors = sum(1 for _ in self._get_recent_errors(minutes=1))
            if recent_errors > self.alert_thresholds['error_rate']:
                self._log_performance_alert('HIGH_ERROR_RATE', {
                    'error_type': error_type,
                    'recent_count': recent_errors,
                    'threshold': self.alert_thresholds['error_rate']
                })
    
    def get_api_performance_stats(self, endpoint: str = None, 
                                minutes: int = 60) -> Dict[str, Any]:
        """获取API性能统计"""
        with self._lock:
            # 获取指定时间范围内的指标
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            
            if endpoint:
                metrics = [m for m in self.api_metrics 
                          if m.endpoint == endpoint and m.timestamp >= cutoff_time]
            else:
                metrics = [m for m in self.api_metrics if m.timestamp >= cutoff_time]
            
            if not metrics:
                return {}
            
            durations = [m.duration for m in metrics]
            status_codes = [m.status_code for m in metrics]
            
            return {
                'endpoint': endpoint or 'all',
                'total_requests': len(metrics),
                'avg_duration': sum(durations) / len(durations),
                'max_duration': max(durations),
                'min_duration': min(durations),
                'p95_duration': self._calculate_percentile(durations, 95),
                'p99_duration': self._calculate_percentile(durations, 99),
                'success_rate': len([c for c in status_codes if c < 400]) / len(status_codes) * 100,
                'error_rate': len([c for c in status_codes if c >= 400]) / len(status_codes) * 100,
                'time_range_minutes': minutes
            }
    
    def get_database_performance_stats(self, minutes: int = 60) -> Dict[str, Any]:
        """获取数据库性能统计"""
        with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            metrics = [m for m in self.db_metrics if m.timestamp >= cutoff_time]
            
            if not metrics:
                return {}
            
            durations = [m.duration for m in metrics]
            query_types = defaultdict(list)
            
            for metric in metrics:
                query_types[metric.query_type].append(metric.duration)
            
            stats = {
                'total_queries': len(metrics),
                'avg_duration': sum(durations) / len(durations),
                'max_duration': max(durations),
                'slow_queries': len([d for d in durations if d > 1.0]),
                'time_range_minutes': minutes,
                'by_query_type': {}
            }
            
            for query_type, type_durations in query_types.items():
                stats['by_query_type'][query_type] = {
                    'count': len(type_durations),
                    'avg_duration': sum(type_durations) / len(type_durations),
                    'max_duration': max(type_durations)
                }
            
            return stats
    
    def get_system_resource_stats(self, minutes: int = 60) -> Dict[str, Any]:
        """获取系统资源统计"""
        with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            metrics = [m for m in self.system_metrics if m.timestamp >= cutoff_time]
            
            if not metrics:
                return self._get_current_system_stats()
            
            cpu_values = [m.cpu_percent for m in metrics]
            memory_values = [m.memory_percent for m in metrics]
            disk_values = [m.disk_usage_percent for m in metrics]
            
            return {
                'cpu': {
                    'current': cpu_values[-1] if cpu_values else 0,
                    'avg': sum(cpu_values) / len(cpu_values),
                    'max': max(cpu_values),
                    'min': min(cpu_values)
                },
                'memory': {
                    'current': memory_values[-1] if memory_values else 0,
                    'avg': sum(memory_values) / len(memory_values),
                    'max': max(memory_values),
                    'min': min(memory_values)
                },
                'disk': {
                    'current': disk_values[-1] if disk_values else 0,
                    'avg': sum(disk_values) / len(disk_values),
                    'max': max(disk_values),
                    'min': min(disk_values)
                },
                'time_range_minutes': minutes,
                'sample_count': len(metrics)
            }
    
    def get_error_stats(self, minutes: int = 60) -> Dict[str, Any]:
        """获取错误统计"""
        with self._lock:
            recent_errors = list(self._get_recent_errors(minutes))
            error_types = defaultdict(int)
            
            for error_type in recent_errors:
                error_types[error_type] += 1
            
            return {
                'total_errors': len(recent_errors),
                'error_types': dict(error_types),
                'time_range_minutes': minutes
            }
    
    def _start_system_monitoring(self):
        """启动系统资源监控"""
        def monitor_system():
            while True:
                try:
                    stats = self._get_current_system_stats()
                    
                    with self._lock:
                        metric = SystemResourceMetric(
                            cpu_percent=stats['cpu_percent'],
                            memory_percent=stats['memory_percent'],
                            disk_usage_percent=stats['disk_usage_percent'],
                            timestamp=datetime.utcnow(),
                            active_connections=stats.get('active_connections', 0)
                        )
                        self.system_metrics.append(metric)
                        
                        # 检查资源使用告警
                        if stats['cpu_percent'] > self.alert_thresholds['cpu_usage']:
                            self._log_performance_alert('HIGH_CPU_USAGE', {
                                'current': stats['cpu_percent'],
                                'threshold': self.alert_thresholds['cpu_usage']
                            })
                        
                        if stats['memory_percent'] > self.alert_thresholds['memory_usage']:
                            self._log_performance_alert('HIGH_MEMORY_USAGE', {
                                'current': stats['memory_percent'],
                                'threshold': self.alert_thresholds['memory_usage']
                            })
                        
                        if stats['disk_usage_percent'] > self.alert_thresholds['disk_usage']:
                            self._log_performance_alert('HIGH_DISK_USAGE', {
                                'current': stats['disk_usage_percent'],
                                'threshold': self.alert_thresholds['disk_usage']
                            })
                    
                    time.sleep(30)  # 每30秒采集一次
                    
                except Exception as e:
                    logger.error(f"系统监控错误: {e}")
                    time.sleep(60)  # 出错时等待更长时间
        
        # 启动后台监控线程
        monitor_thread = threading.Thread(target=monitor_system, daemon=True)
        monitor_thread.start()
    
    def _get_current_system_stats(self) -> Dict[str, float]:
        """获取当前系统状态"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_usage_percent': disk.percent
            }
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                'cpu_percent': 0.0,
                'memory_percent': 0.0,
                'disk_usage_percent': 0.0
            }
    
    def _get_recent_errors(self, minutes: int):
        """获取最近的错误"""
        # 这里简化实现，实际应该从日志或数据库中获取
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        for error_type, count in self.error_counts.items():
            # 简化：假设所有错误都是最近发生的
            yield error_type
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        
        return sorted_values[index]
    
    def _log_performance_alert(self, alert_type: str, details: Dict):
        """记录性能告警"""
        alert_log = {
            'alert_type': alert_type,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.warning(f"性能告警: {json.dumps(alert_log, ensure_ascii=False)}")

# 全局监控实例
_monitor_instance = None

def get_monitor() -> ApplicationMonitor:
    """获取全局监控实例"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ApplicationMonitor()
    return _monitor_instance

def monitor_api_performance(f):
    """API性能监控装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        endpoint = f.__name__
        status_code = 200
        
        try:
            result = f(*args, **kwargs)
            
            # 尝试从Flask响应中获取状态码
            if hasattr(result, 'status_code'):
                status_code = result.status_code
            elif isinstance(result, tuple) and len(result) > 1:
                status_code = result[1]
            
            return result
            
        except Exception as e:
            status_code = 500
            get_monitor().track_error('API_ERROR', str(e), {
                'endpoint': endpoint,
                'args': str(args)[:200],  # 限制长度
                'kwargs': str(kwargs)[:200]
            })
            raise
            
        finally:
            duration = time.time() - start_time
            
            # 获取请求信息（如果在Flask上下文中）
            try:
                from flask import request
                method = request.method
                user_agent = request.headers.get('User-Agent', '')
                ip_address = request.remote_addr or ''
            except:
                method = 'UNKNOWN'
                user_agent = ''
                ip_address = ''
            
            get_monitor().track_api_performance(
                endpoint=endpoint,
                duration=duration,
                status_code=status_code,
                method=method,
                user_agent=user_agent,
                ip_address=ip_address
            )
    
    return decorated_function

def monitor_database_query(query_type: str, table_name: str = ''):
    """数据库查询性能监控装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            rows_affected = 0
            
            try:
                result = f(*args, **kwargs)
                
                # 尝试获取影响的行数
                if hasattr(result, 'rowcount'):
                    rows_affected = result.rowcount
                elif isinstance(result, (list, tuple)):
                    rows_affected = len(result)
                
                return result
                
            except Exception as e:
                get_monitor().track_error('DATABASE_ERROR', str(e), {
                    'query_type': query_type,
                    'table_name': table_name
                })
                raise
                
            finally:
                duration = time.time() - start_time
                get_monitor().track_database_performance(
                    query_type=query_type,
                    duration=duration,
                    table_name=table_name,
                    rows_affected=rows_affected
                )
        
        return decorated_function
    return decorator