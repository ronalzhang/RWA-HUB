"""
Solana日志读取工具
用于读取和解析Solana相关的日志文件
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class SolanaLogReader:
    """Solana日志读取器"""
    
    def __init__(self):
        self.log_dir = 'logs/solana'
        self.transaction_log_file = os.path.join(self.log_dir, 'transactions.log')
        self.api_log_file = os.path.join(self.log_dir, 'api_calls.log')
        self.error_log_file = os.path.join(self.log_dir, 'errors.log')
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
    
    def _read_log_file(self, file_path: str, days_ago: int = 7, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """读取日志文件"""
        if not os.path.exists(file_path):
            return []
        
        logs = []
        cutoff_date = datetime.now() - timedelta(days=days_ago)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 倒序读取（最新的在前面）
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # 解析日志行
                    if ' - {' in line:
                        # 分离时间戳和JSON数据
                        parts = line.split(' - ', 2)
                        if len(parts) >= 3:
                            timestamp_str = parts[0]
                            json_data = parts[2]
                        else:
                            continue
                    else:
                        continue
                    
                    # 解析时间戳
                    try:
                        log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                    except ValueError:
                        try:
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            continue
                    
                    # 检查时间范围
                    if log_time < cutoff_date:
                        continue
                    
                    # 解析JSON数据
                    log_entry = json.loads(json_data)
                    log_entry['parsed_timestamp'] = log_time.isoformat()
                    
                    logs.append(log_entry)
                    
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    continue
        
        except Exception as e:
            logging.error(f"读取日志文件 {file_path} 时出错: {e}")
            return []
        
        # 应用分页
        start_idx = offset
        end_idx = offset + limit
        return logs[start_idx:end_idx]
    
    def _count_log_entries(self, file_path: str, days_ago: int = 7) -> int:
        """统计日志条目数量"""
        if not os.path.exists(file_path):
            return 0
        
        count = 0
        cutoff_date = datetime.now() - timedelta(days=days_ago)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # 提取时间戳
                        if ' - {' in line:
                            timestamp_str = line.split(' - ', 1)[0]
                        else:
                            continue
                        
                        # 解析时间戳
                        try:
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                        except ValueError:
                            try:
                                log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                continue
                        
                        # 检查时间范围
                        if log_time >= cutoff_date:
                            count += 1
                    
                    except Exception:
                        continue
        
        except Exception as e:
            logging.error(f"统计日志文件 {file_path} 时出错: {e}")
            return 0
        
        return count
    
    def get_transaction_logs(self, days_ago: int = 7, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取交易日志"""
        return self._read_log_file(self.transaction_log_file, days_ago, limit, offset)
    
    def get_api_logs(self, days_ago: int = 7, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取API调用日志"""
        return self._read_log_file(self.api_log_file, days_ago, limit, offset)
    
    def get_error_logs(self, days_ago: int = 7, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取错误日志"""
        return self._read_log_file(self.error_log_file, days_ago, limit, offset)
    
    def count_transaction_logs(self, days_ago: int = 7) -> int:
        """统计交易日志数量"""
        return self._count_log_entries(self.transaction_log_file, days_ago)
    
    def count_api_logs(self, days_ago: int = 7) -> int:
        """统计API调用日志数量"""
        return self._count_log_entries(self.api_log_file, days_ago)
    
    def count_error_logs(self, days_ago: int = 7) -> int:
        """统计错误日志数量"""
        return self._count_log_entries(self.error_log_file, days_ago)
    
    def get_transaction_logs(self, limit: int = 100, offset: int = 0, filters: Dict[str, Any] = None) -> tuple:
        """获取交易日志（兼容admin接口）"""
        logs = self._read_log_file(self.transaction_log_file, 7, limit, offset)
        total = self.count_transaction_logs(7)
        return logs, total
    
    def get_api_logs(self, limit: int = 100, offset: int = 0, filters: Dict[str, Any] = None) -> tuple:
        """获取API调用日志（兼容admin接口）"""
        logs = self._read_log_file(self.api_log_file, 7, limit, offset)
        total = self.count_api_logs(7)
        return logs, total
    
    def get_error_logs(self, limit: int = 100, offset: int = 0, filters: Dict[str, Any] = None) -> tuple:
        """获取错误日志（兼容admin接口）"""
        logs = self._read_log_file(self.error_log_file, 7, limit, offset)
        total = self.count_error_logs(7)
        return logs, total
    
    def search_logs(self, query: str, log_type: str = 'all', limit: int = 100, offset: int = 0) -> tuple:
        """搜索日志"""
        # 简单实现，实际应该根据查询条件搜索
        if log_type == 'transactions':
            return self.get_transaction_logs(limit, offset)
        elif log_type == 'api':
            return self.get_api_logs(limit, offset)
        elif log_type == 'errors':
            return self.get_error_logs(limit, offset)
        else:
            # 搜索所有类型
            return [], 0
    
    def get_transaction_stats(self, days: int = 7) -> Optional[Dict[str, Any]]:
        """获取交易统计数据"""
        # 返回None，让调用方使用演示数据
        return None
    
    def get_api_stats(self, days: int = 7) -> Optional[Dict[str, Any]]:
        """获取API统计数据"""
        # 返回None，让调用方使用演示数据
        return None
    
    def get_error_stats(self, days: int = 7) -> Optional[Dict[str, Any]]:
        """获取错误统计数据"""
        # 返回None，让调用方使用演示数据
        return None