import os
import json
import logging
from datetime import datetime
from pathlib import Path

# 确保日志目录存在
def init_solana_logger():
    """初始化Solana日志系统"""
    log_dir = Path('logs/solana')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建交易日志文件
    if not (log_dir / 'transactions.log').exists():
        with open(log_dir / 'transactions.log', 'w') as f:
            pass
    
    # 创建API调用日志文件
    if not (log_dir / 'api_calls.log').exists():
        with open(log_dir / 'api_calls.log', 'w') as f:
            pass
    
    # 创建错误日志文件
    if not (log_dir / 'errors.log').exists():
        with open(log_dir / 'errors.log', 'w') as f:
            pass
    
    return log_dir

# 初始化日志目录
log_dir = init_solana_logger()

def log_transaction(transaction_data):
    """记录交易日志
    
    Args:
        transaction_data (dict): 包含交易信息的字典，必须包含以下字段:
            - transaction_id: 交易ID
            - wallet_address: 钱包地址
            - type: 交易类型 (transfer, mint, burn等)
            - amount: 金额
            - token: 代币类型
            - status: 状态 (success, failed等)
            - block_number: 区块编号
    """
    try:
        log_entry = transaction_data.copy()
        
        # 添加时间戳
        if 'timestamp' not in log_entry:
            log_entry['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 写入日志文件
        with open(log_dir / 'transactions.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
    except Exception as e:
        logging.error(f"记录交易日志时出错: {str(e)}")

def log_api_call(api_data):
    """记录API调用日志
    
    Args:
        api_data (dict): 包含API调用信息的字典，必须包含以下字段:
            - request_id: 请求ID
            - method: 请求方法 (GET, POST等)
            - endpoint: API端点
            - params: 请求参数
            - response_time: 响应时间(秒)
            - status_code: HTTP状态码
            - client_ip: 客户端IP地址
    """
    try:
        log_entry = api_data.copy()
        
        # 添加时间戳
        if 'timestamp' not in log_entry:
            log_entry['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 将params字段转为字符串
        if 'params' in log_entry and not isinstance(log_entry['params'], str):
            log_entry['params'] = json.dumps(log_entry['params'])
        
        # 写入日志文件
        with open(log_dir / 'api_calls.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
    except Exception as e:
        logging.error(f"记录API调用日志时出错: {str(e)}")

def log_error(error_data):
    """记录错误日志
    
    Args:
        error_data (dict): 包含错误信息的字典，必须包含以下字段:
            - error_id: 错误ID
            - level: 错误级别 (ERROR, WARNING, CRITICAL等)
            - message: 错误消息
            - component: 出错的组件
            - stack_trace: 堆栈跟踪(可选)
    """
    try:
        log_entry = error_data.copy()
        
        # 添加时间戳
        if 'timestamp' not in log_entry:
            log_entry['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 写入日志文件
        with open(log_dir / 'errors.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
    except Exception as e:
        logging.error(f"记录错误日志时出错: {str(e)}")

# 初始化日志系统
init_solana_logger() 