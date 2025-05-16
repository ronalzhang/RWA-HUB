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
        
        logger.info(f"使用RPC地址: {rpc_url}")
        
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
                
                logger.info(f"发送Solana RPC请求 (尝试 {retry_count+1}/{max_retries}): {tx_hash}")
                
                # 发送 RPC 请求
                response = requests.post(rpc_url, headers=headers, data=json.dumps(payload), timeout=30)
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
                import traceback
                logger.error(traceback.format_exc())
            
            retry_count += 1
            time.sleep(retry_interval)

        # ----- 更新数据库状态 -----
        try:
            from app.models.asset import Asset, AssetStatus
            
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
                logger.info(f"资产状态更新为 CONFIRMED (状态值:{AssetStatus.CONFIRMED.value}): AssetID={asset_id}")

                # --- 触发上链流程 --- (在数据库提交后进行)
                try:
                    logger.info(f"支付已确认，开始触发资产上链流程: AssetID={asset_id}")
                    
                    from app.blockchain.asset_service import AssetService
                    asset_service = AssetService()
                    deploy_result = asset_service.deploy_asset_to_blockchain(asset_id)
                    
                    if deploy_result.get('success'):
                        logger.info(f"资产上链成功: AssetID={asset_id}, TokenAddress={deploy_result.get('token_address')}")
                        # 状态已在deploy_asset_to_blockchain中更新为ON_CHAIN(状态2)
                    else:
                        logger.error(f"资产上链失败: AssetID={asset_id}, Error: {deploy_result.get('error')}")
                        # 状态已在deploy_asset_to_blockchain中更新为DEPLOYMENT_FAILED(状态7)
                except Exception as deploy_err:
                    logger.error(f"触发或执行上链流程失败: AssetID={asset_id}, Error: {str(deploy_err)}")
                    asset.status = AssetStatus.DEPLOYMENT_FAILED.value
                    asset.error_message = f"触发上链失败: {str(deploy_err)}"
                    db.session.commit()
                    logger.info(f"资产状态更新为 DEPLOYMENT_FAILED (状态值:{AssetStatus.DEPLOYMENT_FAILED.value}): AssetID={asset_id}")

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
                logger.warning(f"资产状态更新为 PAYMENT_FAILED (状态值:{AssetStatus.PAYMENT_FAILED.value}): AssetID={asset_id}, Error: {asset.error_message}")
            else:
                # 达到最大重试次数，状态未定
                asset.status = AssetStatus.PENDING.value
                asset.error_message = "支付确认超时，状态未知"
                
                details = json.loads(asset.payment_details) if asset.payment_details else {}
                details['status'] = 'timeout'
                details['timeout_at'] = datetime.utcnow().isoformat()
                asset.payment_details = json.dumps(details)
                
                db.session.commit()
                logger.warning(f"支付确认超时，资产状态保持 PENDING (状态值:{AssetStatus.PENDING.value}): AssetID={asset_id}")

        except Exception as db_err:
            logger.error(f"更新资产数据库状态失败: AssetID={asset_id}, Error: {str(db_err)}")
            import traceback
            logger.error(traceback.format_exc())
            db.session.rollback()

def auto_monitor_pending_payments():
    """
    自动监控所有状态为PENDING且有payment_tx_hash的资产，触发支付确认监控任务
    此任务应定期执行，检查是否有需要确认的支付交易
    """
    logger.info("开始自动监控待处理的支付交易...")
    
    from app import create_app
    app = create_app()
    with app.app_context():
        try:
            from app.models.asset import Asset, AssetStatus
            
            # 查询所有PENDING状态且有payment_tx_hash的资产
            pending_assets = Asset.query.filter(
                Asset.status == AssetStatus.PENDING.value,
                Asset.payment_tx_hash.isnot(None),
                Asset.payment_confirmed.is_(False)
            ).all()
            
            if not pending_assets:
                logger.info("没有需要监控的待处理支付交易")
                return
                
            logger.info(f"找到 {len(pending_assets)} 个待处理的支付交易")
            
            # 为每个资产触发支付确认监控任务
            for asset in pending_assets:
                try:
                    # 检查是否有支付确认记录
                    if asset.payment_confirmed:
                        logger.info(f"资产 {asset.id} 支付已确认，跳过")
                        continue
                        
                    # 检查是否有错误消息
                    if asset.error_message and ('支付交易失败' in asset.error_message or '支付确认超时' in asset.error_message):
                        # 如果上次检查失败，清除错误信息以便重新检查
                        asset.error_message = None
                        db.session.commit()
                        
                    logger.info(f"为资产 {asset.id} 触发支付确认监控任务，交易哈希: {asset.payment_tx_hash}")
                    monitor_creation_payment.delay(asset.id, asset.payment_tx_hash)
                    
                except Exception as e:
                    logger.error(f"处理资产 {asset.id} 时发生错误: {str(e)}")
            
            logger.info("待处理支付交易监控完成")
            
        except Exception as e:
            logger.error(f"自动监控支付交易失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())


# 创建定期任务
auto_monitor_payments_task = DelayedTask(auto_monitor_pending_payments)

# 系统启动时触发一次，之后每5分钟执行一次
def start_scheduled_tasks():
    """启动定时任务"""
    logger.info("启动定时任务...")
    
    # 立即执行一次
    auto_monitor_payments_task.delay()
    
    # 每5分钟执行一次
    import threading
    def run_scheduler():
        while True:
            time.sleep(300)  # 5分钟
            auto_monitor_payments_task.delay()
    
    # 启动后台线程
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    logger.info("定时任务已启动")

# 应用启动时启动定时任务
start_scheduled_tasks()

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