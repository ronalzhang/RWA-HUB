#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异步任务处理模块
提供后台任务处理功能，如交易监控、状态更新等
"""

import logging
import time
from datetime import datetime
import threading
from threading import Thread
from queue import Queue
import requests
import json

from flask import current_app
from app.extensions import db
from app.models import Asset, Trade, AssetStatus

# 获取日志记录器
logger = logging.getLogger(__name__)

# 任务队列
task_queue = Queue()

# 标记任务处理器是否已启动
task_processor_started = False

class DelayedTask:
    """延迟任务对象，用于模拟Celery的delay方法"""
    
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._add_to_queue()
    
    def _add_to_queue(self):
        task_queue.put((self.func, self.args, self.kwargs))
        _ensure_task_processor_running()
    
    @classmethod
    def delay(cls, *args, **kwargs):
        """模拟Celery的delay方法"""
        return cls(*args, **kwargs)

def _ensure_task_processor_running():
    """确保任务处理器正在运行"""
    global task_processor_started
    if not task_processor_started:
        task_processor_started = True
        t = Thread(target=_process_tasks)
        t.daemon = True
        t.start()
        logger.info("任务处理器已启动")

def _process_tasks():
    """处理队列中的任务"""
    while True:
        try:
            func, args, kwargs = task_queue.get()
            try:
                logger.info(f"执行任务: {func.__name__}, 参数: {args}, {kwargs}")
                func(*args, **kwargs)
            except Exception as e:
                logger.error(f"执行任务出错: {str(e)}")
            finally:
                task_queue.task_done()
        except Exception as e:
            logger.error(f"任务处理器出错: {str(e)}")
            time.sleep(1)  # 防止过于频繁的错误日志

def monitor_transaction_confirmation(tx_signature, trade_id, max_retries=30, retry_interval=10):
    """
    监控交易确认状态
    
    Args:
        tx_signature (str): 交易签名
        trade_id (int): 交易记录ID
        max_retries (int): 最大重试次数
        retry_interval (int): 重试间隔(秒)
    """
    logger.info(f"开始监控交易确认状态: 签名={tx_signature}, 交易ID={trade_id}")
    
    # 获取Solana RPC地址
    from app.config import Config
    rpc_url = Config.SOLANA_RPC_URL or 'https://api.mainnet-beta.solana.com'
    
    # 重试计数器
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # 构造RPC请求
            headers = {
                'Content-Type': 'application/json'
            }
            payload = {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'getTransaction',
                'params': [
                    tx_signature,
                    {
                        'encoding': 'json',
                        'commitment': 'confirmed'
                    }
                ]
            }
            
            # 发送RPC请求
            response = requests.post(rpc_url, headers=headers, data=json.dumps(payload))
            response_data = response.json()
            
            # 检查交易确认状态
            if 'result' in response_data and response_data['result']:
                confirmed = response_data['result'].get('meta', {}).get('err') is None
                
                if confirmed:
                    logger.info(f"交易已确认: {tx_signature}")
                    _update_transaction_status(trade_id, tx_signature, 'confirmed')
                    return
                else:
                    error = response_data['result'].get('meta', {}).get('err')
                    logger.warning(f"交易失败: {tx_signature}, 错误: {error}")
                    _update_transaction_status(trade_id, tx_signature, 'failed', error)
                    return
            
            # 交易尚未确认，继续重试
            logger.info(f"交易尚未确认，等待中... ({retry_count+1}/{max_retries})")
            retry_count += 1
            time.sleep(retry_interval)
        
        except Exception as e:
            logger.error(f"检查交易状态出错: {str(e)}")
            retry_count += 1
            time.sleep(retry_interval)
    
    # 达到最大重试次数，设置为待人工审核
    logger.warning(f"达到最大重试次数，交易状态未确定: {tx_signature}")
    _update_transaction_status(trade_id, tx_signature, 'pending_review', '达到最大重试次数，需人工审核')

def _update_transaction_status(trade_id, tx_signature, status, error=None):
    """
    更新交易状态
    
    Args:
        trade_id (int): 交易记录ID
        tx_signature (str): 交易签名
        status (str): 交易状态
        error (str, optional): 错误信息
    """
    try:
        # 使用应用上下文
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # 获取交易记录
            trade = Trade.query.get(trade_id)
            if not trade:
                logger.error(f"找不到交易记录: ID={trade_id}")
                return
            
            # 更新交易状态
            old_status = trade.status
            trade.status = status
            
            if status == 'confirmed':
                trade.confirmed_at = datetime.utcnow()
                
                # 如果是资产支付交易，更新资产状态
                if trade.asset_id:
                    asset = Asset.query.get(trade.asset_id)
                    if asset:
                        asset.status = AssetStatus.ACTIVE.value  # 激活资产
                        asset.payment_confirmed = True
                        asset.payment_confirmed_at = datetime.utcnow()
                        
                        # 更新资产支付详情
                        try:
                            payment_details = json.loads(asset.payment_details) if asset.payment_details else {}
                            payment_details['status'] = 'confirmed'
                            payment_details['confirmed_at'] = datetime.utcnow().isoformat()
                            asset.payment_details = json.dumps(payment_details)
                        except Exception as e:
                            logger.error(f"更新资产支付详情失败: {str(e)}")
                        
                        logger.info(f"资产支付已确认，已激活资产: ID={asset.id}")
            
            elif status == 'failed':
                # 记录失败原因
                trade.error_message = error
                
                # 如果是资产支付交易，更新资产支付状态
                if trade.asset_id:
                    asset = Asset.query.get(trade.asset_id)
                    if asset:
                        # 更新资产支付详情
                        try:
                            payment_details = json.loads(asset.payment_details) if asset.payment_details else {}
                            payment_details['status'] = 'failed'
                            payment_details['error'] = error
                            payment_details['failed_at'] = datetime.utcnow().isoformat()
                            asset.payment_details = json.dumps(payment_details)
                        except Exception as e:
                            logger.error(f"更新资产支付详情失败: {str(e)}")
                        
                        logger.warning(f"资产支付失败: ID={asset.id}, 错误: {error}")
            
            # 保存更改
            db.session.commit()
            
            logger.info(f"已更新交易状态: ID={trade_id}, 状态: {old_status} → {status}")
    
    except Exception as e:
        logger.error(f"更新交易状态失败: {str(e)}")

def run_task(func_name, *args, **kwargs):
    """
    运行一个任务
    
    Args:
        func_name (str): 任务函数名称
        *args: 位置参数
        **kwargs: 关键字参数
    """
    try:
        # 获取任务函数
        if func_name == 'monitor_transaction_confirmation':
            return monitor_transaction_confirmation(*args, **kwargs)
        else:
            logger.error(f"未知的任务函数: {func_name}")
    except Exception as e:
        logger.error(f"运行任务 {func_name} 出错: {str(e)}")

# 导出延迟任务对象，使其可以被其他模块使用
monitor_transaction_confirmation = DelayedTask(run_task, 'monitor_transaction_confirmation') 