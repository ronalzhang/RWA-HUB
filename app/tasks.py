#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异步任务处理模块
提供后台任务处理功能，如交易监控、状态更新等
"""

import logging
import time
import traceback
from datetime import datetime
import threading
from threading import Thread
from queue import Queue
import requests
import json

from flask import current_app
from app.extensions import db
from app.models import Asset, Trade, AssetStatus, AssetStatusHistory
from app.blockchain.asset_service import AssetService
# 导入app模块的logger
# from app import logger
logger = logging.getLogger(__name__)
from sqlalchemy import exc

# 任务队列
task_queue = Queue()

# 标记任务处理器是否已启动
task_processor_started = False

# 并发控制锁
asset_locks = {}
asset_locks_lock = threading.Lock()

def get_asset_lock(asset_id):
    """获取资产锁，用于并发控制"""
    with asset_locks_lock:
        if asset_id not in asset_locks:
            asset_locks[asset_id] = threading.Lock()
        return asset_locks[asset_id]

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
        # 确保在delay调用时立即添加任务到队列
        self._add_to_queue(*args, **kwargs)
        # logger.info(f"任务已添加到队列: func={self.func.__name__}, args={args}, kwargs={kwargs}")
        logger.debug(f"任务已添加到队列: func={self.func.__name__}, args={args}, kwargs={kwargs}")
        return self

def _ensure_task_processor_running():
    """确保任务处理器正在运行"""
    global task_processor_started
    if not task_processor_started:
        task_processor_started = True
        t = Thread(target=_process_tasks)
        t.daemon = True
        t.start()
        # logger.info("任务处理器已启动")
        logger.debug("任务处理器已启动")

def _process_tasks():
    """处理队列中的任务"""
    while True:
        try:
            func, args, kwargs = task_queue.get()
            try:
                # logger.info(f"执行任务: {func.__name__}, 参数: {args}, {kwargs}")
                logger.debug(f"执行任务: func={func.__name__}, args={args}, kwargs={kwargs}")
                func(*args, **kwargs)
            except Exception as e:
                logger.error(f"执行任务出错: {func.__name__} - {str(e)}")
                logger.error(traceback.format_exc())
            finally:
                task_queue.task_done()
        except Exception as e:
            logger.error(f"任务处理器出错: {str(e)}")
            time.sleep(1)  # 防止过于频繁的错误日志

def get_flask_app():
    """获取Flask应用上下文，避免循环导入"""
    try:
        # 首先尝试从current_app获取
        try:
            from flask import current_app
            if current_app:
                app_obj = current_app._get_current_object()
                logger.debug("从current_app获取Flask应用上下文成功")
                return app_obj
        except Exception as ca_err:
            logger.debug(f"从current_app获取Flask应用上下文失败: {str(ca_err)}")
            pass
        
        # 如果无法从current_app获取，则直接创建新的Flask应用实例
        try:
            from flask import Flask
            from config import Config
            
            # 直接创建Flask应用实例
            app_obj = Flask(__name__.split('.')[0])
            app_obj.config.from_object(Config)
            
            # 初始化基本的扩展，但不需要完整初始化
            from app.extensions import db
            db.init_app(app_obj)
            
            logger.debug("直接创建新的Flask应用实例成功")
            return app_obj
        except Exception as flask_err:
            logger.error(f"直接创建Flask应用实例失败: {str(flask_err)}")
            logger.error(traceback.format_exc())
            raise
    except Exception as e:
        logger.error(f"获取Flask应用上下文失败: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def update_asset_status(asset_id, status, error_message=None, details=None):
    """更新资产状态并记录历史"""
    try:
        asset = Asset.query.get(asset_id)
        if not asset:
            logger.error(f"更新状态时未找到资产: AssetID={asset_id}")
            return False
        
        old_status = asset.status
        asset.status = status
        
        if error_message:
            asset.error_message = error_message
        
        if details:
            if hasattr(asset, 'payment_details') and details.get('payment_related'):
                current_details = json.loads(asset.payment_details) if asset.payment_details else {}
                current_details.update(details)
                asset.payment_details = json.dumps(current_details)
            elif hasattr(asset, 'blockchain_details') and details.get('blockchain_related'):
                current_details = json.loads(asset.blockchain_details) if asset.blockchain_details else {}
                current_details.update(details)
                asset.blockchain_details = json.dumps(current_details)
        
        # 记录状态变更历史
        if hasattr(Asset, 'status_history') and old_status != status:
            history = AssetStatusHistory(
                asset_id=asset_id,
                old_status=old_status,
                new_status=status,
                change_time=datetime.utcnow(),
                change_reason=error_message or f"状态更新: {old_status} -> {status}"
            )
            db.session.add(history)
        
        db.session.commit()
        logger.info(f"资产状态更新: AssetID={asset_id}, {old_status} -> {status}")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新资产状态失败: AssetID={asset_id}, Error: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def monitor_creation_payment(asset_id, tx_hash, max_retries=30, retry_interval=10):
    """
    监控资产创建支付交易的确认状态，并触发后续流程
    
    Args:
        asset_id (int): 资产ID
        tx_hash (str): 支付交易哈希
        max_retries (int): 最大重试次数
        retry_interval (int): 重试间隔(秒)
    """
    # 获取该资产的锁，确保不会有并发处理
    with get_asset_lock(asset_id):
        logger.info(f"开始监控创建支付: AssetID={asset_id}, TxHash={tx_hash}")
        
        app_context = get_flask_app()
        if not app_context:
            logger.error(f"无法获取应用上下文，取消监控支付: AssetID={asset_id}")
            return
        
        with app_context.app_context(): # 确保使用 app_context()
            try:
                # 获取 Solana RPC 地址
                from config import Config # 移到 app_context 内部
                rpc_url = Config.SOLANA_RPC_URL or 'https://api.mainnet-beta.solana.com'
                
                # 使用事务锁防止并发问题
                try:
                    # 首先检查资产当前状态，确保不重复处理
                    asset = db.session.query(Asset).with_for_update(nowait=True).get(asset_id)
                    
                    if not asset:
                        logger.error(f"未找到资产: AssetID={asset_id}")
                        return
                        
                    # 如果资产已经不是PENDING或PAYMENT_PROCESSING状态，或已支付确认，或已上链，则不处理
                    if asset.status not in [AssetStatus.PENDING.value, AssetStatus.PAYMENT_PROCESSING.value]:
                        logger.info(f"资产 {asset_id} 已不是PENDING或PAYMENT_PROCESSING状态 (当前: {asset.status})，跳过支付确认")
                        return
                        
                    if asset.payment_confirmed:
                        logger.info(f"资产 {asset_id} 支付已确认，跳过重复处理")
                        return
                        
                    if asset.token_address:
                        logger.info(f"资产 {asset_id} 已存在上链信息 (地址: {asset.token_address})，跳过支付确认")
                        return
                        
                    # 检查是否有其他进程正在处理该资产
                    if (asset.deployment_in_progress and
                        asset.deployment_started_at and
                        (datetime.utcnow() - asset.deployment_started_at).total_seconds() < 3600): # 1小时超时
                        logger.info(f"资产 {asset_id} 正在被其他进程处理中 (开始于 {asset.deployment_started_at})，跳过")
                        return
                        
                    # 标记正在处理
                    asset.deployment_in_progress = True
                    asset.deployment_started_at = datetime.utcnow()
                    db.session.commit()
                
                except exc.OperationalError:
                    # 捕获数据库锁冲突，表示有其他进程正在处理
                    logger.warning(f"另一个进程已锁定资产 {asset_id} 进行处理，跳过")
                    return
                
                retry_count = 0
                confirmed = False
                transaction_error = None
                
                # logger.info(f"使用RPC地址: {rpc_url}")
                logger.debug(f"AssetID={asset_id}: 使用RPC地址: {rpc_url} 监控 {tx_hash}")
                
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
                        
                        # logger.info(f"发送Solana RPC请求 (尝试 {retry_count+1}/{max_retries}): {tx_hash}")
                        if retry_count == 0 or (retry_count + 1) % 5 == 0 or retry_count == max_retries -1 :
                             logger.info(f"AssetID={asset_id}: 发送Solana RPC请求 (尝试 {retry_count+1}/{max_retries}) for Tx: {tx_hash}")
                        else:
                            logger.debug(f"AssetID={asset_id}: 发送Solana RPC请求 (尝试 {retry_count+1}/{max_retries}) for Tx: {tx_hash}")
                        
                        # 发送 RPC 请求
                        response = requests.post(rpc_url, headers=headers, data=json.dumps(payload), timeout=30) # 增加超时
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
                            # logger.info(f"支付交易尚未确认，可能仍在处理中... (AssetID={asset_id}, TxHash={tx_hash}, 尝试 {retry_count+1}/{max_retries})")
                            logger.debug(f"AssetID={asset_id}: Tx {tx_hash} 尚未确认 (尝试 {retry_count+1}/{max_retries})")

                    except requests.exceptions.Timeout:
                        logger.warning(f"AssetID={asset_id}: Solana RPC请求超时 (尝试 {retry_count+1}/{max_retries}) for Tx: {tx_hash}")
                    except requests.exceptions.RequestException as req_err:
                        logger.error(f"AssetID={asset_id}: 检查交易状态时 RPC 请求失败 (尝试 {retry_count+1}/{max_retries}): {str(req_err)}")
                    except Exception as e:
                        logger.error(f"AssetID={asset_id}: 检查交易状态时发生未知错误 (尝试 {retry_count+1}/{max_retries}): {str(e)}")
                        logger.error(traceback.format_exc())
                    
                    retry_count += 1
                    time.sleep(retry_interval)

                # ----- 更新数据库状态 -----
                try:
                    # 重新获取资产，确保使用最新数据
                    asset = db.session.query(Asset).with_for_update().get(asset_id)
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
                        
                        # 记录状态变更历史
                        if hasattr(Asset, 'status_history'):
                            history = AssetStatusHistory(
                                asset_id=asset_id,
                                old_status=AssetStatus.PENDING.value,
                                new_status=AssetStatus.CONFIRMED.value,
                                change_time=datetime.utcnow(),
                                change_reason="支付确认成功"
                            )
                            db.session.add(history)
                        
                        db.session.commit()
                        logger.info(f"资产状态更新为 CONFIRMED (状态值:{AssetStatus.CONFIRMED.value}): AssetID={asset_id}")

                        # --- 触发上链流程 --- (在数据库提交后进行)
                        try:
                            # 保持deployment_in_progress为True，继续处理上链
                            logger.info(f"支付已确认，开始触发资产上链流程: AssetID={asset_id}")
                            
                            from app.blockchain.asset_service import AssetService
                            asset_service = AssetService()
                            
                            # 执行上链操作
                            deploy_result = asset_service.deploy_asset_to_blockchain(asset_id)
                            
                            # 处理上链结果
                            if deploy_result.get('success'):
                                logger.info(f"资产上链成功: AssetID={asset_id}, TokenAddress={deploy_result.get('token_address')}")
                                # 状态已在deploy_asset_to_blockchain中更新为ON_CHAIN(状态2)
                            else:
                                logger.error(f"资产上链失败: AssetID={asset_id}, Error: {deploy_result.get('error')}")
                                # 添加更详细的错误日志
                                logger.error(f"上链失败详情: {json.dumps(deploy_result, indent=2)}")
                                # 状态已在deploy_asset_to_blockchain中更新为DEPLOYMENT_FAILED(状态7)
                            
                        except Exception as deploy_err:
                            logger.error(f"触发或执行上链流程失败: AssetID={asset_id}, Error: {str(deploy_err)}")
                            logger.error(traceback.format_exc())
                            
                            # 获取最新资产状态
                            asset = db.session.query(Asset).with_for_update().get(asset_id)
                            if asset:
                                asset.status = AssetStatus.DEPLOYMENT_FAILED.value
                                asset.error_message = f"触发上链失败: {str(deploy_err)}"
                                
                                # 记录状态变更历史
                                if hasattr(Asset, 'status_history'):
                                    history = AssetStatusHistory(
                                        asset_id=asset_id,
                                        old_status=AssetStatus.CONFIRMED.value,
                                        new_status=AssetStatus.DEPLOYMENT_FAILED.value,
                                        change_time=datetime.utcnow(),
                                        change_reason=f"上链失败: {str(deploy_err)}"
                                    )
                                    db.session.add(history)
                                
                                db.session.commit()
                                logger.info(f"资产状态更新为 DEPLOYMENT_FAILED (状态值:{AssetStatus.DEPLOYMENT_FAILED.value}): AssetID={asset_id}")
                        finally:
                            # 清除上链进行中标记
                            asset = db.session.query(Asset).with_for_update().get(asset_id)
                            if asset:
                                asset.deployment_in_progress = False
                                db.session.commit()
                                logger.info(f"清除资产上链处理标记: AssetID={asset_id}")

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
                        
                        # 记录状态变更历史
                        if hasattr(Asset, 'status_history'):
                            history = AssetStatusHistory(
                                asset_id=asset_id,
                                old_status=AssetStatus.PENDING.value,
                                new_status=AssetStatus.PAYMENT_FAILED.value,
                                change_time=datetime.utcnow(),
                                change_reason=f"支付失败: {str(transaction_error)}"
                            )
                            db.session.add(history)
                        
                        # 清除上链进行中标记
                        asset.deployment_in_progress = False
                        
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
                        
                        # 清除上链进行中标记
                        asset.deployment_in_progress = False
                        
                        db.session.commit()
                        logger.warning(f"支付确认超时，资产状态保持 PENDING (状态值:{AssetStatus.PENDING.value}): AssetID={asset_id}")
                        
                        # 添加定时重试逻辑
                        if retry_count >= max_retries:
                            logger.info(f"AssetID={asset_id}: 达到最大重试次数 ({max_retries}) for Tx {tx_hash}，安排30分钟后再次尝试监控。")
                            # 30分钟后再次尝试
                            def delayed_retry_func(): # 确保函数名唯一或使用lambda
                                logger.info(f"AssetID={asset_id}: 执行延时重试任务 for Tx {tx_hash}")
                                monitor_creation_payment_task.delay(asset_id, tx_hash)
                            
                            retry_thread = Thread(target=delayed_retry_func)
                            retry_thread.daemon = True
                            retry_thread.start()

                except Exception as db_err:
                    logger.error(f"更新资产数据库状态失败: AssetID={asset_id}, Error: {str(db_err)}")
                    logger.error(traceback.format_exc())
                    db.session.rollback()
                    
                    # 清除处理标记，允许后续重试
                    try:
                        asset = Asset.query.get(asset_id)
                        if asset:
                            asset.deployment_in_progress = False
                            db.session.commit()
                    except:
                        db.session.rollback()
                        
            except Exception as outer_err:
                logger.error(f"监控支付确认过程中发生错误: AssetID={asset_id}, Error: {str(outer_err)}")
                logger.error(traceback.format_exc())
                
                # 确保清除处理标记
                try:
                    with db.session.begin():
                        asset = Asset.query.get(asset_id)
                        if asset:
                            asset.deployment_in_progress = False
                except:
                    pass
                    
            finally:
                logger.info(f"完成监控创建支付: AssetID={asset_id}, TxHash={tx_hash}")

def auto_monitor_pending_payments():
    """自动监控待处理的支付交易 和 资产上链"""
    try:
        logger.info("开始执行周期性任务：自动监控待处理支付及资产上链...")
        
        flask_app = get_flask_app()
        if not flask_app:
            logger.error("无法获取应用上下文，取消自动监控")
            return
        
        with flask_app.app_context():
            try:
                # 0. 查找PAYMENT_PROCESSING状态的资产，触发支付确认监控
                payment_processing_assets = Asset.query.filter(
                    Asset.status == AssetStatus.PAYMENT_PROCESSING.value,
                    Asset.payment_tx_hash != None,
                    Asset.payment_confirmed != True
                ).limit(20).all()
                
                if payment_processing_assets:
                    logger.info(f"找到 {len(payment_processing_assets)} 个支付处理中的资产，开始监控支付确认...")
                    
                    for asset in payment_processing_assets:
                        try:
                            logger.info(f"触发资产 {asset.id} 的支付确认监控 (TxHash: {asset.payment_tx_hash})")
                            # 触发支付确认监控任务
                            monitor_creation_payment_task.delay(asset.id, asset.payment_tx_hash)
                        except Exception as e:
                            logger.error(f"触发资产 {asset.id} 支付确认监控失败: {str(e)}")
                else:
                    logger.debug("没有找到支付处理中的资产。")
                
                # 1. 查找已支付确认但未上链的资产
                confirmed_assets = Asset.query.filter(
                    Asset.payment_confirmed == True,
                    Asset.token_address == None,
                    Asset.deployment_in_progress != True,
                    Asset.status == AssetStatus.CONFIRMED.value
                ).limit(10).all()
                
                if confirmed_assets:
                    logger.info(f"找到 {len(confirmed_assets)} 个已支付确认但待上链的资产，开始处理...")
                    
                    for asset in confirmed_assets:
                        with get_asset_lock(asset.id):
                            logger.info(f"开始处理资产 {asset.id} 的上链流程 (通过auto_monitor)")
                            try:
                                # 使用事务锁确保此资产不会被并发处理
                                asset_for_update = db.session.query(Asset).with_for_update(nowait=True).get(asset.id)
                                
                                # 再次检查条件，确保在获取锁后资产状态仍然符合预期
                                if not asset_for_update or asset_for_update.status != AssetStatus.CONFIRMED.value or asset_for_update.token_address is not None:
                                    logger.info(f"资产 {asset.id} 状态已变更或已上链，跳过 (当前状态: {asset_for_update.status if asset_for_update else 'Not Found'})")
                                    continue

                                if asset_for_update.deployment_in_progress:
                                    logger.info(f"资产 {asset.id} 已经在处理中 (auto_monitor)，跳过")
                                    continue
                                
                                # 标记开始处理
                                asset_for_update.deployment_in_progress = True
                                asset_for_update.deployment_started_at = datetime.utcnow()
                                db.session.commit()
                                
                                # 创建自动上链历史记录
                                try:
                                    from app.models.admin import OnchainHistory
                                    onchain_record = OnchainHistory.create_record(
                                        asset_id=asset.id,
                                        trigger_type='auto_monitor',
                                        onchain_type='asset_creation',
                                        triggered_by='system'
                                    )
                                    logger.info(f"已创建自动监控上链历史记录: {onchain_record.id}")
                                except Exception as e:
                                    logger.error(f"创建自动监控上链历史记录失败: {str(e)}")
                                    # 不影响主流程，继续执行
                                
                                # 调用上链服务
                                service = AssetService()
                                result = service.deploy_asset_to_blockchain(asset.id)
                                
                                if result.get('success'):
                                    logger.info(f"资产 {asset.id} 通过 auto_monitor 已成功部署，地址: {result.get('token_address')}")
                                else:
                                    logger.error(f"资产 {asset.id} 通过 auto_monitor 部署失败: {result.get('error')}")
                                    # deploy_asset_to_blockchain 应该自己处理失败状态的更新
                                    # 但这里可以确保 deployment_in_progress 被清除
                                    asset_recheck = Asset.query.get(asset.id)
                                    if asset_recheck:
                                        asset_recheck.deployment_in_progress = False
                                        db.session.commit()
                                
                            except exc.OperationalError:
                                logger.warning(f"资产 {asset.id} 已被另一个进程锁定 (auto_monitor)，跳过处理")
                            except Exception as e:
                                logger.error(f"处理资产 {asset.id} 上链时出错 (auto_monitor): {str(e)}")
                                logger.error(traceback.format_exc())
                                # 清理标记
                                asset_recheck_exc = Asset.query.get(asset.id)
                                if asset_recheck_exc:
                                     asset_recheck_exc.deployment_in_progress = False
                                     db.session.commit()
                else:
                    logger.debug("没有找到已支付确认但待上链的资产。")
                
                # 2. 清理超时的部署标记（超过2小时的）
                timeout_assets = Asset.query.filter(
                    Asset.deployment_in_progress == True,
                    Asset.deployment_started_at != None
                ).all()
                
                current_time = datetime.utcnow()
                for asset in timeout_assets:
                    time_diff = (current_time - asset.deployment_started_at).total_seconds()
                    if time_diff > 7200:  # 2小时超时
                        logger.warning(f"清理超时的部署标记: AssetID={asset.id}, 开始时间: {asset.deployment_started_at}, 超时: {time_diff}秒")
                        asset.deployment_in_progress = False
                        asset.error_message = f"部署超时（{time_diff}秒），已清理标记"
                        db.session.commit()
                
                # 3. 检查部署失败的资产，如果失败时间超过30分钟，尝试重新部署
                failed_assets = Asset.query.filter(
                    Asset.status == AssetStatus.DEPLOYMENT_FAILED.value,
                    Asset.payment_confirmed == True,
                    Asset.token_address == None,
                    Asset.deployment_in_progress != True
                ).limit(5).all()  # 限制重试数量
                
                for asset in failed_assets:
                    # 检查失败时间（如果有记录的话）
                    should_retry = True
                    if hasattr(asset, 'updated_at') and asset.updated_at:
                        time_since_failure = (current_time - asset.updated_at).total_seconds()
                        if time_since_failure < 1800:  # 30分钟内不重试
                            should_retry = False
                    
                    if should_retry:
                        logger.info(f"尝试重新部署失败的资产: AssetID={asset.id}")
                        # 重置状态为CONFIRMED，让正常流程处理
                        asset.status = AssetStatus.CONFIRMED.value
                        asset.error_message = None
                        db.session.commit()
                    
            except Exception as e:
                logger.error(f"周期性任务执行内部失败: {str(e)}")
                logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"周期性任务执行最外层失败: {str(e)}")
        logger.error(traceback.format_exc())


# 创建定期任务
auto_monitor_payments_task = DelayedTask(auto_monitor_pending_payments)

# 任务调度器初始化标志
scheduler_initialized = False

# 系统启动时触发一次，之后每5分钟执行一次
def start_scheduled_tasks():
    """启动定时任务"""
    global scheduler_initialized
    
    # 如果已经初始化过，直接返回
    if scheduler_initialized:
        # logger.info("定时任务已经初始化，跳过重复初始化")
        logger.debug("定时任务已经初始化，跳过重复初始化")
        return
        
    logger.info("启动定时任务...")
    
    try:
        # 立即执行一次自动监控
        logger.info("系统启动：立即触发一次周期性任务 (监控支付及上链)...")
        auto_monitor_pending_payments()
        
        # 每5分钟执行一次
        from app.extensions import scheduler # 确保 scheduler 已初始化
        
        # 确保任务只添加一次
        if not scheduler.get_job('auto_monitor_all_assets'): # 更改任务ID
            scheduler.add_job(
                id='auto_monitor_all_assets', # 更改任务ID
                func=auto_monitor_pending_payments,
                trigger='interval',
                minutes=5, # 5分钟频率是否合适需要评估
                replace_existing=True
            )
            logger.info("周期性任务 (监控支付及上链) 已添加到调度器: 每5分钟执行一次")
        else:
            logger.info("周期性任务 (监控支付及上链) 已存在，跳过添加")
        
        # 设置全局初始化标志
        scheduler_initialized = True
        logger.info("定时任务模块已启动")
    except Exception as e:
        logger.error(f"启动定时任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

# 应用启动时启动定时任务
# 注意: 这行代码不会在应用启动时立即执行，需要在app/__init__.py中显式调用
# start_scheduled_tasks()

# 保存原始函数的引用
_original_monitor_creation_payment = monitor_creation_payment

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
            return _original_monitor_creation_payment(*args, **kwargs)
        else:
            logger.error(f"未知的任务函数: {func_name}")
    except Exception as e:
        logger.error(f"运行任务 {func_name} 出错: {str(e)}")
        logger.error(traceback.format_exc())

# 导出延迟任务对象
monitor_creation_payment_task = DelayedTask(_original_monitor_creation_payment)

# 如果还需要监控购买交易确认，可以添加类似的任务
# def monitor_purchase_confirmation(trade_id, tx_hash, ...):
#     ...
# monitor_purchase_confirmation = DelayedTask(monitor_purchase_confirmation) 