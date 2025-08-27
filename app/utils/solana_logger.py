"""
Solana日志记录工具
用于记录Solana相关的交易、API调用和错误信息
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# 创建日志目录
SOLANA_LOG_DIR = 'logs/solana'
os.makedirs(SOLANA_LOG_DIR, exist_ok=True)

# 日志文件路径
TRANSACTION_LOG_FILE = os.path.join(SOLANA_LOG_DIR, 'transactions.log')
API_LOG_FILE = os.path.join(SOLANA_LOG_DIR, 'api_calls.log')
ERROR_LOG_FILE = os.path.join(SOLANA_LOG_DIR, 'errors.log')

def init_solana_logger():
    """初始化Solana日志系统"""
    loggers = {}
    
    # 交易日志器
    transaction_logger = logging.getLogger('solana.transactions')
    transaction_handler = logging.FileHandler(TRANSACTION_LOG_FILE)
    transaction_formatter = logging.Formatter('%(asctime)s - %(message)s')
    transaction_handler.setFormatter(transaction_formatter)
    transaction_logger.addHandler(transaction_handler)
    transaction_logger.setLevel(logging.INFO)
    loggers['transactions'] = transaction_logger
    
    # API调用日志器
    api_logger = logging.getLogger('solana.api_calls')
    api_handler = logging.FileHandler(API_LOG_FILE)
    api_formatter = logging.Formatter('%(asctime)s - %(message)s')
    api_handler.setFormatter(api_formatter)
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.INFO)
    loggers['api_calls'] = api_logger
    
    # 错误日志器
    error_logger = logging.getLogger('solana.errors')
    error_handler = logging.FileHandler(ERROR_LOG_FILE)
    error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    error_handler.setFormatter(error_formatter)
    error_logger.addHandler(error_handler)
    error_logger.setLevel(logging.ERROR)
    loggers['errors'] = error_logger
    
    return loggers

def log_transaction(transaction_data: Dict[str, Any]):
    """记录交易日志"""
    try:
        logger = logging.getLogger('solana.transactions')
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'transaction',
            'data': transaction_data
        }
        logger.info(json.dumps(log_entry, ensure_ascii=False))
    except Exception as e:
        print(f"记录交易日志时出错: {e}")

def log_api_call(api_data: Dict[str, Any]):
    """记录API调用日志"""
    try:
        logger = logging.getLogger('solana.api_calls')
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'api_call',
            'data': api_data
        }
        logger.info(json.dumps(log_entry, ensure_ascii=False))
    except Exception as e:
        print(f"记录API调用日志时出错: {e}")

def log_error(error_data: Dict[str, Any]):
    """记录错误日志"""
    try:
        logger = logging.getLogger('solana.errors')
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'error',
            'data': error_data
        }
        logger.error(json.dumps(log_entry, ensure_ascii=False))
    except Exception as e:
        print(f"记录错误日志时出错: {e}")