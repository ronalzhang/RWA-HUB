#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异步任务处理模块
提供后台任务处理功能，如交易监控、状态更新等
"""

import logging
import time
import traceback
import json
from datetime import datetime

from flask import current_app
from app.extensions import db
from app.models import Asset, AssetStatus, AssetStatusHistory, TaskQueue, TaskStatus
from app.blockchain.asset_service import AssetService
from sqlalchemy import exc

logger = logging.getLogger(__name__)

# --- 新的数据库任务队列系统 ---

def schedule_task(task_name, **kwargs):
    """将一个新任务安排到数据库队列中"""
    try:
        task = TaskQueue(
            task_name=task_name,
            task_args=kwargs,
            status=TaskStatus.PENDING.value
        )
        db.session.add(task)
        db.session.commit()
        logger.info(f"新任务已入队: {task_name}, 参数: {kwargs}")
        return task
    except Exception as e:
        logger.error(f"任务入队失败: {task_name}, Error: {str(e)}")
        db.session.rollback()
        return None


def _execute_task(task):
    """执行单个任务的逻辑"""
    logger.info(f"开始执行任务 #{task.id}: {task.task_name}")
    try:
        if task.task_name == 'monitor_creation_payment':
            # 从参数中获取 asset_id 和 tx_hash
            asset_id = task.task_args.get('asset_id')
            tx_hash = task.task_args.get('tx_hash')
            if not all([asset_id, tx_hash]):
                raise ValueError("任务 monitor_creation_payment 缺少 asset_id 或 tx_hash 参数")
            
            # 调用实际的工作函数
            monitor_creation_payment(asset_id, tx_hash)
        else:
            raise ValueError(f"未知的任务名称: {task.task_name}")
        
        # 如果没有异常，标记为完成
        task.status = TaskStatus.COMPLETED.value
        task.error_message = None
        logger.info(f"任务 #{task.id} 执行成功.")

    except Exception as e:
        logger.error(f"任务 #{task.id} ({task.task_name}) 执行失败: {str(e)}")
        logger.error(traceback.format_exc())
        task.status = TaskStatus.FAILED.value
        task.error_message = str(e)

# --- 核心任务函数 ---

def monitor_creation_payment(asset_id, tx_hash, max_retries=30, retry_interval=10):
    """
    监控资产创建支付交易的确认状态，并触发后续流程。
    这是一个阻塞函数，由任务处理器在后台调用。
    """
    logger.info(f"开始监控创建支付: AssetID={asset_id}, TxHash={tx_hash}")
    
    # 此函数现在在一个已经有app_context的后台任务中运行，所以不需要再手动创建
    from config import Config
    rpc_url = Config.SOLANA_RPC_URL or 'https://api.mainnet-beta.solana.com'
    
    retry_count = 0
    confirmed = False
    transaction_error = None
    
    while retry_count < max_retries:
        try:
            headers = {'Content-Type': 'application/json'}
            payload = {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'getTransaction',
                'params': [
                    tx_hash,
                    {'encoding': 'json', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}
                ]
            }
            response = requests.post(rpc_url, headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            response_data = response.json()
            
            if 'result' in response_data and response_data['result']:
                if response_data['result'].get('meta', {}).get('err') is None:
                    confirmed = True
                    logger.info(f"资产创建支付已确认: AssetID={asset_id}, TxHash={tx_hash}")
                    break
                else:
                    transaction_error = response_data['result']['meta']['err']
                    logger.warning(f"资产创建支付交易失败: AssetID={asset_id}, Error: {transaction_error}")
                    break
        except Exception as e:
            logger.error(f"检查交易状态时发生错误 (尝试 {retry_count+1}/{max_retries}): {str(e)}")
        
        retry_count += 1
        time.sleep(retry_interval)

    # ----- 更新数据库状态 -----
    asset = Asset.query.get(asset_id)
    if not asset:
        logger.error(f"在更新状态时未找到资产: AssetID={asset_id}")
        raise ValueError(f"Asset {asset_id} not found")

    if confirmed:
        asset.payment_confirmed = True
        asset.payment_confirmed_at = datetime.utcnow()
        asset.status = AssetStatus.CONFIRMED.value
        logger.info(f"资产状态更新为 CONFIRMED: AssetID={asset_id}")
        # 注意：后续的上链流程将由主定时任务的资产巡检部分处理
    elif transaction_error is not None:
        asset.status = AssetStatus.PAYMENT_FAILED.value
        asset.error_message = f"支付交易失败: {str(transaction_error)}"
        logger.warning(f"资产状态更新为 PAYMENT_FAILED: AssetID={asset_id}")
    else:
        asset.status = AssetStatus.PAYMENT_FAILED.value # 超时也标记为失败
        asset.error_message = "支付确认超时，状态未知"
        logger.warning(f"支付确认超时，资产状态更新为 PAYMENT_FAILED: AssetID={asset_id}")
    
    db.session.commit()


# --- 主定时任务（系统心跳） ---

def process_background_jobs():
    """系统后台主任务，由APScheduler定时调用。"""
    try:
        logger.info("开始执行后台任务和资产监控...")
        
        flask_app = get_flask_app()
        if not flask_app:
            logger.error("无法获取应用上下文，取消执行")
            return
        
        with flask_app.app_context():
            # 1. 执行数据库队列中的待处理任务
            pending_tasks = TaskQueue.query.filter_by(status=TaskStatus.PENDING.value).order_by(TaskQueue.created_at).limit(10).all()
            if pending_tasks:
                logger.info(f"找到 {len(pending_tasks)} 个待处理的任务，开始执行...")
                for task in pending_tasks:
                    try:
                        task.status = TaskStatus.RUNNING.value
                        db.session.commit()
                        
                        _execute_task(task)
                        
                        db.session.commit() # 提交任务执行后的状态变更
                    except Exception as e:
                        logger.error(f"执行任务 #{task.id} 的外层捕获到异常: {e}")
                        db.session.rollback()
                        task.status = TaskStatus.FAILED.value
                        task.error_message = f"外层异常: {e}"
                        db.session.commit()
            else:
                logger.debug("没有在数据库中找到待处理的任务。")

            # 2. 监控已支付确认但未上链的资产
            confirmed_assets = Asset.query.filter(
                Asset.status == AssetStatus.CONFIRMED.value,
                Asset.token_address.is_(None),
                Asset.deployment_in_progress != True
            ).limit(10).all()
            
            if confirmed_assets:
                logger.info(f"找到 {len(confirmed_assets)} 个已支付确认但待上链的资产，开始处理...")
                for asset in confirmed_assets:
                    logger.info(f"开始处理资产 {asset.id} 的上链流程 (通过定时任务)")
                    service = AssetService()
                    service.deploy_asset_to_blockchain(asset.id)
            else:
                logger.debug("没有找到已支付确认但待上链的资产。")

            # 3. 检查并重试部署失败的资产 (已包含新的重试逻辑)
            MAX_DEPLOYMENT_RETRIES = 5
            failed_assets = Asset.query.filter(
                Asset.status == AssetStatus.DEPLOYMENT_FAILED.value,
                Asset.payment_confirmed == True,
                Asset.token_address.is_(None),
                Asset.deployment_in_progress != True,
                Asset.deployment_retry_count < MAX_DEPLOYMENT_RETRIES,
                Asset.deleted_at.is_(None)
            ).limit(5).all()

            current_time = datetime.utcnow()
            for asset in failed_assets:
                retry_delay = 600 * (2 ** asset.deployment_retry_count)
                time_since_failure = (current_time - asset.updated_at).total_seconds()

                if time_since_failure > retry_delay:
                    logger.info(f"资产 {asset.id} 符合重试条件 (第 {asset.deployment_retry_count + 1} 次)，准备重试。")
                    asset.deployment_retry_count += 1
                    asset.status = AssetStatus.CONFIRMED.value
                    asset.error_message = f"准备进行第 {asset.deployment_retry_count} 次重新部署"
                    db.session.commit()
                else:
                    logger.debug(f"资产 {asset.id} 部署失败，正在等待下一个重试周期 (还需等待 {int(retry_delay - time_since_failure)} 秒)")

    except Exception as e:
        logger.error(f"后台主任务执行失败: {str(e)}")
        logger.error(traceback.format_exc())


def get_flask_app():
    """获取Flask应用上下文，避免循环导入"""
    try:
        from flask import current_app
        if current_app:
            return current_app._get_current_object()
    except Exception:
        pass
    from app import create_app
    return create_app()

# --- 定时任务启动器 ---

scheduler_initialized = False

def start_scheduled_tasks():
    """启动定时任务"""
    global scheduler_initialized
    if scheduler_initialized:
        return
        
    logger.info("启动后台主任务调度器...")
    try:
        from app.extensions import scheduler
        if not scheduler.get_job('process_background_jobs'):
            scheduler.add_job(
                id='process_background_jobs',
                func=process_background_jobs,
                trigger='interval',
                minutes=1, # 缩短为1分钟，以便更快地处理队列任务
                replace_existing=True
            )
            logger.info("后台主任务已添加到调度器: 每分钟执行一次")
        else:
            logger.info("后台主任务已在调度器中存在")
        
        scheduler_initialized = True
        logger.info("后台主任务调度器已启动")
    except Exception as e:
        logger.error(f"启动后台主任务调度器失败: {str(e)}")
        logger.error(traceback.format_exc())
