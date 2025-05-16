import os
import json
import datetime
from collections import defaultdict
import re

class SolanaLogReader:
    """Solana日志读取服务类"""
    
    def __init__(self):
        self.log_dir = os.path.join('logs', 'solana')
        self.transaction_log_path = os.path.join(self.log_dir, 'transactions.log')
        self.api_log_path = os.path.join(self.log_dir, 'api_calls.log')
        self.error_log_path = os.path.join(self.log_dir, 'errors.log')
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
    
    def get_transaction_logs(self, limit=20, offset=0, filters=None):
        """获取交易日志
        
        Args:
            limit: 返回的日志条数限制
            offset: 分页偏移量
            filters: 筛选条件，dict格式 {field: value}
            
        Returns:
            tuple: (日志记录列表, 总记录数)
        """
        logs, total = self._read_log_file(self.transaction_log_path, limit, offset, filters)
        return logs, total
    
    def get_api_logs(self, limit=20, offset=0, filters=None):
        """获取API调用日志
        
        Args:
            limit: 返回的日志条数限制
            offset: 分页偏移量
            filters: 筛选条件，dict格式 {field: value}
            
        Returns:
            tuple: (日志记录列表, 总记录数)
        """
        logs, total = self._read_log_file(self.api_log_path, limit, offset, filters)
        return logs, total
    
    def get_error_logs(self, limit=20, offset=0, filters=None):
        """获取错误日志
        
        Args:
            limit: 返回的日志条数限制
            offset: 分页偏移量
            filters: 筛选条件，dict格式 {field: value}
            
        Returns:
            tuple: (日志记录列表, 总记录数)
        """
        logs, total = self._read_log_file(self.error_log_path, limit, offset, filters)
        return logs, total
    
    def search_logs(self, query, log_type='all', limit=20, offset=0):
        """全文搜索所有类型的日志
        
        Args:
            query: 搜索关键字
            log_type: 日志类型 ('transaction', 'api', 'error', 'all')
            limit: 返回的日志条数限制
            offset: 分页偏移量
            
        Returns:
            tuple: (日志记录列表, 总记录数)
        """
        query = query.lower()
        all_logs = []
        
        # 根据日志类型确定需要搜索的文件列表
        log_files = []
        if log_type in ['all', 'transaction']:
            log_files.append(self.transaction_log_path)
        if log_type in ['all', 'api']:
            log_files.append(self.api_log_path)
        if log_type in ['all', 'error']:
            log_files.append(self.error_log_path)
        
        # 搜索所有指定的日志文件
        for log_file in log_files:
            if not os.path.exists(log_file):
                continue
                
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        # 转换所有文本值为小写进行搜索
                        if self._log_contains_query(log_entry, query):
                            all_logs.append(log_entry)
                    except (json.JSONDecodeError, ValueError) as e:
                        continue
        
        # 按时间戳排序（最新的在前）
        all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 分页处理
        total = len(all_logs)
        logs = all_logs[offset:offset+limit] if offset < total else []
        
        return logs, total
    
    def get_transaction_stats(self, days=7):
        """获取交易统计数据
        
        Args:
            days: 统计的天数
            
        Returns:
            dict: 统计数据
        """
        if not os.path.exists(self.transaction_log_path):
            return None
            
        # 计算起始日期
        cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 统计数据初始化
        daily_transactions = defaultdict(int)
        daily_volume = defaultdict(float)
        token_distribution = defaultdict(float)
        total_transactions = 0
        successful_transactions = 0
        failed_transactions = 0
        
        with open(self.transaction_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log = json.loads(line.strip())
                    timestamp = log.get('timestamp', '')
                    
                    # 跳过超出时间范围的记录
                    if timestamp < cutoff_date:
                        continue
                    
                    # 提取日期部分
                    date = timestamp.split('T')[0]
                    
                    # 计数
                    total_transactions += 1
                    daily_transactions[date] += 1
                    
                    # 计算交易成功/失败
                    status = log.get('status', '')
                    if status == 'success':
                        successful_transactions += 1
                    else:
                        failed_transactions += 1
                    
                    # 交易金额
                    amount = float(log.get('amount', 0))
                    daily_volume[date] += amount
                    
                    # 代币分布
                    token = log.get('token', 'UNKNOWN')
                    token_distribution[token] += amount
                    
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        
        # 转换代币分布为列表格式
        token_dist_list = [
            {'token': token, 'amount': amount}
            for token, amount in token_distribution.items()
        ]
        
        # 构建返回数据
        return {
            'total_transactions': total_transactions,
            'successful_transactions': successful_transactions,
            'failed_transactions': failed_transactions,
            'total_volume': sum(daily_volume.values()),
            'daily_transactions': daily_transactions,
            'daily_volume': daily_volume,
            'token_distribution': token_dist_list
        }
    
    def get_api_stats(self, days=7):
        """获取API调用统计数据
        
        Args:
            days: 统计的天数
            
        Returns:
            dict: 统计数据
        """
        if not os.path.exists(self.api_log_path):
            return None
            
        # 计算起始日期
        cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 统计数据初始化
        daily_calls = defaultdict(int)
        endpoint_distribution = defaultdict(int)
        total_calls = 0
        successful_calls = 0
        failed_calls = 0
        response_times = []
        
        with open(self.api_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log = json.loads(line.strip())
                    timestamp = log.get('timestamp', '')
                    
                    # 跳过超出时间范围的记录
                    if timestamp < cutoff_date:
                        continue
                    
                    # 提取日期部分
                    date = timestamp.split('T')[0]
                    
                    # 计数
                    total_calls += 1
                    daily_calls[date] += 1
                    
                    # 端点统计
                    endpoint = log.get('endpoint', '/unknown')
                    endpoint_distribution[endpoint] += 1
                    
                    # 状态统计
                    status_code = log.get('status_code', 0)
                    if 200 <= status_code < 400:
                        successful_calls += 1
                    else:
                        failed_calls += 1
                    
                    # 响应时间
                    response_time = log.get('response_time')
                    if response_time is not None:
                        response_times.append(float(response_time))
                    
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        
        # 计算平均响应时间
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # 转换端点分布为列表格式
        endpoint_dist_list = [
            {'endpoint': endpoint, 'count': count}
            for endpoint, count in endpoint_distribution.items()
        ]
        # 按调用次数排序，降序
        endpoint_dist_list.sort(key=lambda x: x['count'], reverse=True)
        
        # 构建返回数据
        return {
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'failed_calls': failed_calls,
            'average_response_time': avg_response_time,
            'daily_calls': daily_calls,
            'endpoint_distribution': endpoint_dist_list[:10]  # 只返回前10个
        }
    
    def get_error_stats(self, days=7):
        """获取错误统计数据
        
        Args:
            days: 统计的天数
            
        Returns:
            dict: 统计数据
        """
        if not os.path.exists(self.error_log_path):
            return None
            
        # 计算起始日期
        cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 统计数据初始化
        error_distribution = defaultdict(int)
        recent_errors = []
        total_errors = 0
        
        with open(self.error_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log = json.loads(line.strip())
                    timestamp = log.get('timestamp', '')
                    
                    # 跳过超出时间范围的记录
                    if timestamp < cutoff_date:
                        continue
                    
                    # 计数
                    total_errors += 1
                    
                    # 错误类型统计
                    error_type = log.get('type', 'Unknown')
                    error_distribution[error_type] += 1
                    
                    # 收集最近的错误
                    recent_errors.append(log)
                    
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        
        # 按时间排序，最新的在前
        recent_errors.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 转换错误分布为列表格式
        error_dist_list = [
            {'type': error_type, 'count': count}
            for error_type, count in error_distribution.items()
        ]
        # 按错误次数排序，降序
        error_dist_list.sort(key=lambda x: x['count'], reverse=True)
        
        # 构建返回数据
        return {
            'total_errors': total_errors,
            'error_distribution': error_dist_list,
            'recent_errors': recent_errors[:10]  # 只返回前10个
        }
    
    def _read_log_file(self, file_path, limit=20, offset=0, filters=None):
        """从日志文件读取记录
        
        Args:
            file_path: 日志文件路径
            limit: 返回的记录数量限制
            offset: 分页偏移量
            filters: 筛选条件
            
        Returns:
            tuple: (日志记录列表, 总记录数)
        """
        if not os.path.exists(file_path):
            return [], 0
            
        all_logs = []
        filtered_logs = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    all_logs.append(log_entry)
                    
                    # 应用筛选条件
                    if self._apply_filters(log_entry, filters):
                        filtered_logs.append(log_entry)
                except (json.JSONDecodeError, ValueError):
                    continue
        
        # 按时间戳排序
        filtered_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 分页处理
        total = len(filtered_logs)
        logs = filtered_logs[offset:offset+limit] if offset < total else []
        
        return logs, total
    
    def _apply_filters(self, log_entry, filters):
        """应用筛选条件
        
        Args:
            log_entry: 日志条目
            filters: 筛选条件
            
        Returns:
            bool: 是否符合筛选条件
        """
        if not filters:
            return True
            
        for key, value in filters.items():
            # 处理范围筛选
            if key.endswith('_lt'):
                field = key[:-3]  # 移除 _lt 后缀
                if field not in log_entry or log_entry[field] >= value:
                    return False
            elif key.endswith('_gt'):
                field = key[:-3]  # 移除 _gt 后缀
                if field not in log_entry or log_entry[field] <= value:
                    return False
            elif key.endswith('_lte'):
                field = key[:-4]  # 移除 _lte 后缀
                if field not in log_entry or log_entry[field] > value:
                    return False
            elif key.endswith('_gte'):
                field = key[:-4]  # 移除 _gte 后缀
                if field not in log_entry or log_entry[field] < value:
                    return False
            # 处理普通字段匹配
            elif key in log_entry:
                # 如果是字符串，使用部分匹配；否则使用精确匹配
                if isinstance(log_entry[key], str) and isinstance(value, str):
                    if value.lower() not in log_entry[key].lower():
                        return False
                elif log_entry[key] != value:
                    return False
            else:
                # 如果日志条目中没有该字段，视为不匹配
                return False
                
        return True
    
    def _log_contains_query(self, log_entry, query):
        """检查日志记录是否包含查询关键字
        
        Args:
            log_entry: 日志记录
            query: 查询关键字
            
        Returns:
            bool: 是否包含查询关键字
        """
        # 简化版的全文搜索，递归遍历字典字段
        def search_in_dict(d, q):
            for key, value in d.items():
                if isinstance(value, dict):
                    if search_in_dict(value, q):
                        return True
                elif isinstance(value, (list, tuple)):
                    for item in value:
                        if isinstance(item, dict):
                            if search_in_dict(item, q):
                                return True
                        elif isinstance(item, str) and q in item.lower():
                            return True
                elif isinstance(value, str) and q in value.lower():
                    return True
                elif isinstance(key, str) and q in key.lower():
                    return True
            return False
            
        return search_in_dict(log_entry, query) 