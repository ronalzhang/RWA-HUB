from flask import Blueprint, jsonify, request, render_template, current_app, abort, g
from datetime import datetime, timedelta
import json
import os
import re
from collections import defaultdict
import random

from app.utils.solana_log_reader import SolanaLogReader
from app.routes.admin.auth import admin_required, permission_required, admin_page_required

# 创建蓝图
admin_solana_bp = Blueprint('admin_solana', __name__, url_prefix='/admin/solana')

# 创建日志阅读器实例
log_reader = SolanaLogReader()

# 页面路由 - Solana监控仪表盘
@admin_solana_bp.route('/dashboard')
@admin_page_required
def solana_dashboard():
    """Solana监控仪表盘"""
    return render_template('admin/solana/dashboard.html')

# 页面路由 - 交易日志
@admin_solana_bp.route('/transactions')
@admin_page_required
def transaction_logs():
    """Solana交易日志页面"""
    return render_template('admin/solana/transactions.html')

# 页面路由 - API调用日志
@admin_solana_bp.route('/api-logs')
@admin_page_required
def api_logs():
    """Solana API调用日志页面"""
    return render_template('admin/solana/api_logs.html')

# 页面路由 - 错误日志
@admin_solana_bp.route('/error-logs')
@admin_page_required
def error_logs():
    """Solana错误日志页面"""
    return render_template('admin/solana/error_logs.html')

# API路由 - 获取交易日志
@admin_solana_bp.route('/api/transactions')
@admin_required
def get_transactions():
    """获取交易日志API"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # 构建筛选条件
    filters = {}
    for key in ['tx_hash', 'from', 'to', 'status']:
        if request.args.get(key):
            filters[key] = request.args.get(key)
    
    logs, total = log_reader.get_transaction_logs(limit, offset, filters)
    
    return jsonify({
        'logs': logs,
        'total': total
    })

# API路由 - 获取API调用日志
@admin_solana_bp.route('/api/api-logs')
@admin_required
def get_api_logs():
    """获取API调用日志API"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # 构建筛选条件
    filters = {}
    for key in ['endpoint', 'method', 'status_code']:
        if request.args.get(key):
            filters[key] = request.args.get(key)
    
    # 处理响应时间筛选
    response_time = request.args.get('response_time')
    if response_time:
        if response_time == 'fast':
            filters['response_time_lt'] = 100
        elif response_time == 'medium':
            filters['response_time_gte'] = 100
            filters['response_time_lt'] = 500
        elif response_time == 'slow':
            filters['response_time_gte'] = 500
    
    logs, total = log_reader.get_api_logs(limit, offset, filters)
    
    return jsonify({
        'logs': logs,
        'total': total
    })

# API路由 - 获取错误日志
@admin_solana_bp.route('/api/error-logs')
@admin_required
def get_error_logs():
    """获取错误日志API"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # 构建筛选条件
    filters = {}
    for key in ['type', 'message', 'source']:
        if request.args.get(key):
            filters[key] = request.args.get(key)
    
    logs, total = log_reader.get_error_logs(limit, offset, filters)
    
    return jsonify({
        'logs': logs,
        'total': total
    })

# API路由 - 搜索日志
@admin_solana_bp.route('/api/search')
@admin_required
def search_logs():
    """搜索所有类型日志"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    query = request.args.get('query', '')
    log_type = request.args.get('type', 'all')
    
    if not query:
        return jsonify({
            'logs': [],
            'total': 0
        })
    
    logs, total = log_reader.search_logs(query, log_type, limit, offset)
    
    return jsonify({
        'logs': logs,
        'total': total
    })

# API路由 - 交易统计摘要
@admin_solana_bp.route('/api/transaction-summary')
@admin_required
def transaction_summary():
    """获取交易统计摘要"""
    days = request.args.get('days', 7, type=int)
    
    # 获取基础统计数据
    stats = log_reader.get_transaction_stats(days)
    
    # 如果没有真实数据，生成随机数据用于演示
    if not stats:
        stats = generate_demo_transaction_stats(days)
    
    return jsonify(stats)

# API路由 - API调用统计摘要
@admin_solana_bp.route('/api/api-summary')
@admin_required
def api_summary():
    """获取API调用统计摘要"""
    days = request.args.get('days', 7, type=int)
    
    # 获取基础统计数据
    stats = log_reader.get_api_stats(days)
    
    # 如果没有真实数据，生成随机数据用于演示
    if not stats:
        stats = generate_demo_api_stats(days)
    
    return jsonify(stats)

# API路由 - 错误统计摘要
@admin_solana_bp.route('/api/error-summary')
@admin_required
def error_summary():
    """获取错误统计摘要"""
    days = request.args.get('days', 7, type=int)
    
    # 获取基础统计数据
    stats = log_reader.get_error_stats(days)
    
    # 如果没有真实数据，生成随机数据用于演示
    if not stats:
        stats = generate_demo_error_stats()
    
    return jsonify(stats)

# 生成演示用的交易统计数据
def generate_demo_transaction_stats(days):
    """生成随机交易统计数据用于演示"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # 生成日期范围
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    # 生成每日交易数据
    daily_transactions = {}
    daily_volume = {}
    
    for date in date_range:
        daily_transactions[date] = random.randint(50, 500)
        daily_volume[date] = random.randint(1000, 50000)
    
    # 生成代币分布数据
    tokens = ['SOL', 'USDC', 'USDT', 'BTC', 'ETH', 'RAY', 'SRM']
    token_distribution = []
    
    for token in tokens:
        token_distribution.append({
            'token': token,
            'amount': random.randint(1000, 100000)
        })
    
    # 返回完整统计数据
    return {
        'total_transactions': sum(daily_transactions.values()),
        'successful_transactions': int(sum(daily_transactions.values()) * 0.92),
        'failed_transactions': int(sum(daily_transactions.values()) * 0.08),
        'total_volume': sum(daily_volume.values()),
        'daily_transactions': daily_transactions,
        'daily_volume': daily_volume,
        'token_distribution': token_distribution
    }

# 生成演示用的API调用统计数据
def generate_demo_api_stats(days):
    """生成随机API调用统计数据用于演示"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # 生成日期范围
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    # 生成每日API调用数据
    daily_calls = {}
    
    for date in date_range:
        daily_calls[date] = random.randint(500, 5000)
    
    # 生成端点分布数据
    endpoints = [
        '/api/solana/transact',
        '/api/solana/balance',
        '/api/solana/account',
        '/api/solana/token',
        '/api/solana/status'
    ]
    endpoint_distribution = []
    
    for endpoint in endpoints:
        endpoint_distribution.append({
            'endpoint': endpoint,
            'count': random.randint(1000, 10000)
        })
    
    # 计算总调用次数和成功率
    total_calls = sum(daily_calls.values())
    successful_calls = int(total_calls * 0.95)
    failed_calls = total_calls - successful_calls
    
    # 返回完整统计数据
    return {
        'total_calls': total_calls,
        'successful_calls': successful_calls,
        'failed_calls': failed_calls,
        'average_response_time': random.uniform(80, 200),
        'daily_calls': daily_calls,
        'endpoint_distribution': endpoint_distribution
    }

# 生成演示用的错误统计数据
def generate_demo_error_stats():
    """生成随机错误统计数据用于演示"""
    # 生成最近错误记录
    error_types = ['ConnectionError', 'TimeoutError', 'ValidationError', 'AuthenticationError', 'TransactionError']
    error_messages = [
        'Failed to connect to RPC node',
        'Request timed out after 30 seconds',
        'Invalid transaction format',
        'Token account not found',
        'Insufficient funds for transaction',
        'Signature verification failed',
        'Transaction rejected by network'
    ]
    
    recent_errors = []
    for i in range(10):
        error_type = random.choice(error_types)
        error_message = random.choice(error_messages)
        
        # 生成随机时间戳，最近7天内
        days_ago = random.randint(0, 6)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        timestamp = datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        recent_errors.append({
            'timestamp': timestamp.isoformat(),
            'type': error_type,
            'message': error_message,
            'source': random.choice(['client', 'server', 'network']),
            'details': {
                'request_id': f'req_{random.randint(10000, 99999)}',
                'endpoint': random.choice(['/api/solana/transact', '/api/solana/balance', '/api/solana/account'])
            }
        })
    
    # 按时间排序，最新的在前
    recent_errors.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # 返回完整统计数据
    return {
        'total_errors': random.randint(50, 200),
        'error_distribution': [
            {'type': 'ConnectionError', 'count': random.randint(10, 50)},
            {'type': 'TimeoutError', 'count': random.randint(10, 50)},
            {'type': 'ValidationError', 'count': random.randint(10, 50)},
            {'type': 'TransactionError', 'count': random.randint(10, 50)},
            {'type': 'AuthenticationError', 'count': random.randint(5, 20)}
        ],
        'recent_errors': recent_errors
    } 