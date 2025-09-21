"""
交易API模块 - 处理资产交易相关的API请求
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import json
import logging
from app.models import Asset, AssetStatus, Trade, TradeStatus
from app.blockchain.asset_service import AssetService
from app.extensions import db

# 获取日志记录器
logger = logging.getLogger(__name__)

# 创建蓝图（在__init__.py中已定义，这里导入）
from app.routes import trades_api_bp

@trades_api_bp.route('/payment/confirm', methods=['POST'])
def confirm_asset_payment():
    """
    确认资产创建支付并触发上链流程
    
    参数:
    - asset_id: 资产ID
    - tx_hash: 支付交易哈希
    - details: 支付详情（可选）
    """
    try:
        # 获取请求参数
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据为空'
            }), 400
        
        # 验证必要参数
        asset_id = data.get('asset_id')
        tx_hash = data.get('tx_hash')
        
        if not asset_id:
            return jsonify({
                'success': False,
                'error': '缺少资产ID'
            }), 400
            
        if not tx_hash:
            return jsonify({
                'success': False,
                'error': '缺少交易哈希'
            }), 400
        
        # 检查资产是否存在
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({
                'success': False,
                'error': f'资产不存在: {asset_id}'
            }), 404
        
        # 检查是否已经处理过该交易
        if asset.payment_tx_hash == tx_hash and asset.payment_confirmed:
            logger.info(f"交易 {tx_hash} 已经确认过，无需重复处理")
            
            # 返回当前状态
            status_message = "支付已确认"
            if asset.token_address:
                status_message += "且资产已上链"
            elif asset.deployment_in_progress:
                status_message += "，资产正在上链中"
            elif asset.status == AssetStatus.CONFIRMED.value:
                status_message += "，等待上链"
                
            return jsonify({
                'success': True,
                'message': status_message,
                'payment_confirmed': True,
                'asset_id': asset_id,
                'token_address': asset.token_address,
                'status': asset.status,
                'already_processed': True
            }), 200
        
        # 准备支付信息
        payment_info = {
            'tx_hash': tx_hash,
            'confirmed_at': datetime.utcnow().isoformat(),
            'status': 'confirmed',
            'details': data.get('details', {})
        }
        
        # 更新资产支付信息
        asset.payment_tx_hash = tx_hash
        
        # 如果已有payment_details，尝试解析并合并
        if asset.payment_details:
            try:
                existing_details = json.loads(asset.payment_details)
                # 保留原始信息
                for key, value in existing_details.items():
                    if key not in payment_info:
                        payment_info[key] = value
            except:
                # 如果解析失败，不做合并
                pass
                
        # 保存更新的支付信息
        asset.payment_details = json.dumps(payment_info)
        db.session.commit()
        logger.info(f"已更新资产 {asset_id} 的支付信息, 交易哈希: {tx_hash}")
        
        # 使用资产服务处理支付并触发上链
        logger.info(f"开始调用资产服务处理支付确认: AssetID={asset_id}")
        asset_service = AssetService()
        result = asset_service.process_asset_payment(asset_id, payment_info)
        
        # 记录处理结果
        if result.get('success', False):
            logger.info(f"支付确认处理成功: AssetID={asset_id}, 结果: {result}")
        else:
            logger.error(f"支付确认处理失败: AssetID={asset_id}, 错误: {result.get('error', '未知错误')}")
        
        # 返回处理结果
        return jsonify({
            'success': result.get('success', False),
            'message': result.get('message', '支付确认请求已处理'),
            'asset_id': asset_id,
            'payment_processed': result.get('payment_processed', False),
            'token_address': asset.token_address if hasattr(asset, 'token_address') else None,
            'status': asset.status
        }), 200
        
    except Exception as e:
        logger.error(f"确认资产支付失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"处理支付确认请求失败: {str(e)}"
        }), 500

@trades_api_bp.route('/payment/status/<int:asset_id>', methods=['GET'])
def get_payment_status(asset_id):
    """
    获取资产支付状态
    """
    try:
        # 获取资产
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({
                'success': False,
                'error': f'资产不存在: {asset_id}'
            }), 404
            
        # 准备支付状态信息
        status_data = {
            'asset_id': asset_id,
            'payment_confirmed': asset.payment_confirmed,
            'payment_tx_hash': asset.payment_tx_hash,
            'status': asset.status,
            'token_address': asset.token_address,
            'deployment_in_progress': asset.deployment_in_progress
        }
        
        # 添加时间戳信息
        if asset.payment_confirmed_at:
            status_data['payment_confirmed_at'] = asset.payment_confirmed_at.isoformat()
            
        if asset.deployment_started_at:
            status_data['deployment_started_at'] = asset.deployment_started_at.isoformat()
            
        # 添加错误信息（如果有）
        if asset.error_message:
            status_data['error_message'] = asset.error_message
            
        # 添加人性化状态描述
        if asset.status == AssetStatus.ON_CHAIN.value:
            status_data['status_description'] = "已上链"
        elif asset.status == AssetStatus.CONFIRMED.value:
            if asset.deployment_in_progress:
                status_data['status_description'] = "支付已确认，上链处理中"
            else:
                status_data['status_description'] = "支付已确认，等待上链"
        elif asset.status == AssetStatus.PENDING.value:
            if asset.payment_tx_hash:
                status_data['status_description'] = "支付交易已提交，等待确认"
            else:
                status_data['status_description'] = "等待支付"
        elif asset.status == AssetStatus.DEPLOYMENT_FAILED.value:
            status_data['status_description'] = "上链失败"
        elif asset.status == AssetStatus.PAYMENT_FAILED.value:
            status_data['status_description'] = "支付失败"
        else:
            status_data['status_description'] = f"状态码: {asset.status}"
            
        return jsonify({
            'success': True,
            'payment_status': status_data
        }), 200
        
    except Exception as e:
        logger.error(f"获取支付状态失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"获取支付状态失败: {str(e)}"
        }), 500
        
@trades_api_bp.route('/monitor/<int:asset_id>', methods=['POST'])
def trigger_payment_monitoring(asset_id):
    """
    手动触发支付监控任务
    """
    try:
        # 检查资产是否存在
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({
                'success': False,
                'error': f'资产不存在: {asset_id}'
            }), 404
            
        # 检查是否有支付交易哈希
        if not asset.payment_tx_hash:
            return jsonify({
                'success': False,
                'error': f'资产 {asset_id} 没有支付交易哈希，无法监控'
            }), 400
            
        # 检查状态 - 只有PENDING状态的资产才需要监控
        if asset.status != AssetStatus.PENDING.value:
            return jsonify({
                'success': False,
                'error': f'资产状态不是PENDING，当前状态: {asset.status}，无需监控'
            }), 400
            
        # 触发监控任务
        from app.tasks import monitor_creation_payment
        monitor_task = monitor_creation_payment.delay(asset_id, asset.payment_tx_hash)
        
        return jsonify({
            'success': True,
            'message': f'已触发资产 {asset_id} 的支付监控任务',
            'asset_id': asset_id,
            'tx_hash': asset.payment_tx_hash
        }), 200
        
    except Exception as e:
        logger.error(f"触发支付监控失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"触发支付监控失败: {str(e)}"
        }), 500 