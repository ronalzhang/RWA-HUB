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
from app.blockchain.asset_service import AssetService

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
        
        # 不要在初始化时立即添加到队列
        # self._add_to_queue()
    
    def _add_to_queue(self, *extra_args, **extra_kwargs):
        args = self.args + extra_args
        kwargs = {**self.kwargs, **extra_kwargs}
        task_queue.put((self.func, args, kwargs))
        _ensure_task_processor_running()
    
    def delay(self, *args, **kwargs):
        """模拟Celery的delay方法"""
        self._add_to_queue(*args, **kwargs)
        return self

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

def monitor_creation_payment(asset_id, tx_hash, max_retries=30, retry_interval=10):
    """
    监控资产创建支付交易的确认状态，并触发后续流程
    
    Args:
        asset_id (int): 资产ID
        tx_hash (str): 支付交易哈希
        max_retries (int): 最大重试次数
        retry_interval (int): 重试间隔(秒)
    """
    logger.info(f"开始监控创建支付: AssetID={asset_id}, TxHash={tx_hash}")
    
    from app import create_app
    app = create_app()
    with app.app_context():
        # 获取 Solana RPC 地址
        from app.config import Config
        rpc_url = Config.SOLANA_RPC_URL or 'https://api.mainnet-beta.solana.com'
        
        retry_count = 0
        confirmed = False
        transaction_error = None
        
        while retry_count < max_retries:
            try:
                # 构造 RPC 请求
                headers = {'Content-Type': 'application/json'}
                payload = {
                    'jsonrpc': '2.0',
                    'id': 1,
                    'method': 'getTransaction',
                    'params': [
                        tx_hash,
                        {
                            'encoding': 'json',
                            'maxSupportedTransactionVersion': 0,
                            'commitment': 'confirmed'
                        }
                    ]
                }
                
                # 发送 RPC 请求
                response = requests.post(rpc_url, headers=headers, data=json.dumps(payload), timeout=10)
                response.raise_for_status()
                response_data = response.json()
                
                # 检查交易确认状态
                if 'result' in response_data and response_data['result']:
                    transaction_meta = response_data['result'].get('meta', {})
                    if transaction_meta.get('err') is None:
                        confirmed = True
                        logger.info(f"资产创建支付已确认: AssetID={asset_id}, TxHash={tx_hash}")
                        break
                    else:
                        transaction_error = transaction_meta.get('err')
                        logger.warning(f"资产创建支付交易失败: AssetID={asset_id}, TxHash={tx_hash}, Error: {transaction_error}")
                        break
                else:
                    logger.info(f"支付交易尚未确认，可能仍在处理中... (AssetID={asset_id}, TxHash={tx_hash}, 尝试 {retry_count+1}/{max_retries})")

            except requests.exceptions.RequestException as req_err:
                logger.error(f"检查交易状态时 RPC 请求失败: {str(req_err)}")
            except Exception as e:
                logger.error(f"检查交易状态时发生未知错误: {str(e)}")
            
            retry_count += 1
            time.sleep(retry_interval)

        # ----- 更新数据库状态 -----
        try:
            asset = Asset.query.get(asset_id)
            if not asset:
                logger.error(f"在更新状态时未找到资产: AssetID={asset_id}")
                return

            if confirmed:
                # 支付确认成功
                asset.payment_confirmed = True
                asset.payment_confirmed_at = datetime.utcnow()
                asset.status = AssetStatus.CONFIRMED.value
                
                details = json.loads(asset.payment_details) if asset.payment_details else {}
                details['status'] = 'confirmed'
                details['confirmed_at'] = asset.payment_confirmed_at.isoformat()
                asset.payment_details = json.dumps(details)
                
                db.session.commit()
                logger.info(f"资产状态更新为 CONFIRMED: AssetID={asset_id}")

                # --- 触发上链流程 --- (在数据库提交后进行)
                try:
                    logger.info(f"支付已确认，开始触发资产上链流程: AssetID={asset_id}")
                    asset_service = AssetService()
                    deploy_result = asset_service.deploy_asset_to_blockchain(asset_id)
                    logger.info(f"资产上链流程已触发 (结果可能异步): AssetID={asset_id}, Deploy Result Success: {deploy_result.get('success')}")
                except Exception as deploy_err:
                    logger.error(f"触发或执行上链流程失败: AssetID={asset_id}, Error: {str(deploy_err)}")
                    asset.status = AssetStatus.DEPLOYMENT_FAILED.value
                    asset.error_message = f"触发上链失败: {str(deploy_err)}"
                    db.session.commit()

            elif transaction_error is not None:
                # 交易失败
                asset.status = AssetStatus.PAYMENT_FAILED.value
                asset.payment_confirmed = False
                asset.error_message = f"支付交易失败: {str(transaction_error)}"
                
                details = json.loads(asset.payment_details) if asset.payment_details else {}
                details['status'] = 'failed'
                details['error'] = str(transaction_error)
                details['failed_at'] = datetime.utcnow().isoformat()
                asset.payment_details = json.dumps(details)
                
                db.session.commit()
                logger.warning(f"资产状态更新为 PAYMENT_FAILED: AssetID={asset_id}, Error: {asset.error_message}")
            else:
                # 达到最大重试次数，状态未定
                asset.status = AssetStatus.PENDING.value
                asset.error_message = "支付确认超时，状态未知"
                db.session.commit()
                logger.warning(f"支付确认超时，资产状态保持 PENDING: AssetID={asset_id}")

        except Exception as db_err:
            logger.error(f"更新资产数据库状态失败: AssetID={asset_id}, Error: {str(db_err)}")
            db.session.rollback()

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
        if func_name == 'monitor_creation_payment':
            return monitor_creation_payment(*args, **kwargs)
        else:
            logger.error(f"未知的任务函数: {func_name}")
    except Exception as e:
        logger.error(f"运行任务 {func_name} 出错: {str(e)}")

# 导出延迟任务对象
monitor_creation_payment = DelayedTask(run_task, 'monitor_creation_payment')

# 如果还需要监控购买交易确认，可以添加类似的任务
# def monitor_purchase_confirmation(trade_id, tx_hash, ...):
#     ...
# monitor_purchase_confirmation = DelayedTask(monitor_purchase_confirmation) 