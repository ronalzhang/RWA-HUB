#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
健康检查API路由
提供系统健康状态的HTTP端点
"""

from flask import Blueprint, jsonify, request
from app.services.health_check_service import get_health_check_service, HealthStatus
from app.services.application_monitor import get_monitor
from app.services.cache_service import get_cache
from app.services.database_optimizer import get_database_optimizer
from app.services.async_task_processor import get_task_processor
import logging

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__, url_prefix='/api/health')

@health_bp.route('/', methods=['GET'])
def health_check():
    """基础健康检查端点"""
    try:
        health_service = get_health_check_service()
        overall_status, summary = health_service.get_overall_health()
        
        # 根据健康状态设置HTTP状态码
        if overall_status == HealthStatus.HEALTHY:
            status_code = 200
        elif overall_status == HealthStatus.WARNING:
            status_code = 200  # 警告状态仍返回200，但在响应中标明
        else:
            status_code = 503  # 服务不可用
        
        return jsonify(summary), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'overall_status': 'critical',
            'message': f'Health check service error: {str(e)}',
            'timestamp': None
        }), 503

@health_bp.route('/detailed', methods=['GET'])
def detailed_health_check():
    """详细健康检查端点"""
    try:
        health_service = get_health_check_service()
        results = health_service.run_all_checks()
        
        detailed_results = {}
        for name, result in results.items():
            detailed_results[name] = {
                'status': result.status.value,
                'message': result.message,
                'response_time': result.response_time,
                'timestamp': result.timestamp.isoformat(),
                'details': result.details
            }
        
        return jsonify({
            'checks': detailed_results,
            'timestamp': results[list(results.keys())[0]].timestamp.isoformat() if results else None
        })
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return jsonify({
            'error': f'Detailed health check failed: {str(e)}'
        }), 500

@health_bp.route('/check/<check_name>', methods=['GET'])
def single_health_check(check_name):
    """单个健康检查端点"""
    try:
        health_service = get_health_check_service()
        result = health_service.run_check(check_name)
        
        if result.status == HealthStatus.UNKNOWN:
            status_code = 404
        elif result.status == HealthStatus.CRITICAL:
            status_code = 503
        else:
            status_code = 200
        
        return jsonify({
            'name': result.name,
            'status': result.status.value,
            'message': result.message,
            'response_time': result.response_time,
            'timestamp': result.timestamp.isoformat(),
            'details': result.details
        }), status_code
        
    except Exception as e:
        logger.error(f"Single health check failed {check_name}: {e}")
        return jsonify({
            'name': check_name,
            'status': 'critical',
            'message': f'Check failed: {str(e)}',
            'error': True
        }), 500

@health_bp.route('/uptime/<check_name>', methods=['GET'])
def uptime_stats(check_name):
    """获取可用性统计"""
    try:
        hours = request.args.get('hours', 24, type=int)
        if hours <= 0 or hours > 168:  # 限制在1周内
            hours = 24
        
        health_service = get_health_check_service()
        stats = health_service.get_uptime_stats(check_name, hours)
        
        if not stats:
            return jsonify({
                'error': f'No historical data found for check {check_name}'
            }), 404
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Failed to get uptime stats {check_name}: {e}")
        return jsonify({
            'error': f'Failed to get uptime stats: {str(e)}'
        }), 500

@health_bp.route('/performance', methods=['GET'])
def performance_metrics():
    """获取性能指标"""
    try:
        monitor = get_monitor()
        
        # 获取API性能统计
        api_stats = monitor.get_api_performance_stats()
        
        # 获取数据库性能统计
        db_stats = monitor.get_database_performance_stats()
        
        # 获取系统资源统计
        system_stats = monitor.get_system_resource_stats()
        
        # 获取错误统计
        error_stats = monitor.get_error_stats()
        
        return jsonify({
            'api_performance': api_stats,
            'database_performance': db_stats,
            'system_resources': system_stats,
            'error_statistics': error_stats,
            'timestamp': None
        })
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        return jsonify({
            'error': f'Failed to get performance metrics: {str(e)}'
        }), 500

@health_bp.route('/cache/stats', methods=['GET'])
def cache_stats():
    """获取缓存统计信息"""
    try:
        cache = get_cache()
        stats = cache.get_stats()
        
        return jsonify({
            'cache_stats': stats,
            'timestamp': None
        })
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return jsonify({
            'error': f'Failed to get cache stats: {str(e)}'
        }), 500

@health_bp.route('/database/stats', methods=['GET'])
def database_stats():
    """获取数据库统计信息"""
    try:
        db_optimizer = get_database_optimizer()
        
        # 获取表统计信息
        table_stats = db_optimizer.analyze_table_statistics()
        
        # 获取连接池状态
        pool_stats = db_optimizer.monitor_connection_pool()
        
        # 获取数据库大小信息
        size_info = db_optimizer.get_database_size_info()
        
        # 获取慢查询（如果可用）
        slow_queries = db_optimizer.get_slow_queries(limit=5)
        
        return jsonify({
            'table_statistics': table_stats,
            'connection_pool': pool_stats,
            'database_size': size_info,
            'slow_queries': slow_queries,
            'timestamp': None
        })
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return jsonify({
            'error': f'Failed to get database stats: {str(e)}'
        }), 500

@health_bp.route('/tasks/stats', methods=['GET'])
def task_stats():
    """获取后台任务统计信息"""
    try:
        processor = get_task_processor()
        stats = processor.get_queue_stats()
        
        return jsonify({
            'task_processor_stats': stats,
            'timestamp': None
        })
        
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        return jsonify({
            'error': f'Failed to get task stats: {str(e)}'
        }), 500

@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """就绪检查端点 - 用于负载均衡器"""
    try:
        health_service = get_health_check_service()
        
        # 只检查关键服务
        critical_checks = ['database', 'api_endpoints']
        
        all_ready = True
        check_results = {}
        
        for check_name in critical_checks:
            result = health_service.run_check(check_name)
            check_results[check_name] = result.status.value
            
            if result.status == HealthStatus.CRITICAL:
                all_ready = False
        
        if all_ready:
            return jsonify({
                'ready': True,
                'checks': check_results,
                'message': 'Service Ready'
            }), 200
        else:
            return jsonify({
                'ready': False,
                'checks': check_results,
                'message': 'Service Not Ready'
            }), 503
            
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({
            'ready': False,
            'error': str(e)
        }), 503

@health_bp.route('/live', methods=['GET'])
def liveness_check():
    """存活检查端点 - 用于容器编排"""
    try:
        # 简单的存活检查，只要能响应就认为存活
        return jsonify({
            'alive': True,
            'message': 'Service Alive',
            'timestamp': None
        }), 200
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return jsonify({
            'alive': False,
            'error': str(e)
        }), 500

# 错误处理
@health_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Health check endpoint not found',
        'available_endpoints': [
            '/api/health/',
            '/api/health/detailed',
            '/api/health/check/<check_name>',
            '/api/health/uptime/<check_name>',
            '/api/health/performance',
            '/api/health/cache/stats',
            '/api/health/database/stats',
            '/api/health/tasks/stats',
            '/api/health/ready',
            '/api/health/live'
        ]
    }), 404

@health_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Health check service internal error',
        'message': str(error)
    }), 500