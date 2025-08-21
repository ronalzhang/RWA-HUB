#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
区块链API路由 - 提供区块链网络状态和交易监控接口
"""

from flask import Blueprint, jsonify, request
from app.blockchain.solana_service import (
    get_network_health_report, get_connection_metrics,
    force_node_switch, test_all_nodes, estimate_transaction_fee,
    get_account_balance, check_transaction_status
)
from app.blockchain.transaction_manager import transaction_manager
from app.blockchain.transaction_rollback import rollback_manager
from app.services.transaction_monitor import transaction_monitor
from app.utils.decorators import handle_api_errors
from app.models import Asset
from app.blockchain.asset_service import AssetService
from app.utils.error_handler import create_error_response
import logging

logger = logging.getLogger(__name__)

blockchain_api = Blueprint('blockchain_api', __name__, url_prefix='/api/blockchain')

@blockchain_api.route('/network/health', methods=['GET'])
@handle_api_errors
def get_network_health():
    """获取网络健康状态"""
    health_report = get_network_health_report()
    metrics = get_connection_metrics()
    
    return jsonify({
        'success': True,
        'data': {
            'health_report': health_report,
            'metrics': metrics
        }
    })

@blockchain_api.route('/network/switch-node', methods=['POST'])
@handle_api_errors
def switch_node():
    """强制切换到下一个可用节点"""
    result = force_node_switch()
    
    return jsonify({
        'success': result['success'],
        'data': result
    })

@blockchain_api.route('/network/test-nodes', methods=['GET'])
@handle_api_errors
def test_nodes():
    """测试所有节点连通性"""
    test_results = test_all_nodes()
    
    return jsonify({
        'success': True,
        'data': test_results
    })

@blockchain_api.route('/transaction/fee-estimate', methods=['GET'])
@handle_api_errors
def get_fee_estimate():
    """获取交易费用估算"""
    transaction_type = request.args.get('type', 'transfer')
    
    fee_estimate = estimate_transaction_fee(transaction_type)
    
    return jsonify({
        'success': True,
        'data': fee_estimate
    })

@blockchain_api.route('/account/balance', methods=['GET'])
@handle_api_errors
def get_balance():
    """获取账户余额"""
    address = request.args.get('address')
    token_mint = request.args.get('token_mint')
    
    if not address:
        return jsonify({
            'success': False,
            'error': '缺少地址参数'
        }), 400
    
    balance_info = get_account_balance(address, token_mint)
    
    return jsonify({
        'success': True,
        'data': balance_info
    })

@blockchain_api.route('/transaction/monitor/statistics', methods=['GET'])
@handle_api_errors
def get_monitor_statistics():
    """获取交易监控统计"""
    stats = transaction_monitor.get_monitoring_statistics()
    
    return jsonify({
        'success': True,
        'data': stats
    })

@blockchain_api.route('/transaction/monitor/active', methods=['GET'])
@handle_api_errors
def get_active_transactions():
    """获取活跃交易列表"""
    transactions = transaction_monitor.get_active_transactions()
    
    return jsonify({
        'success': True,
        'data': {
            'transactions': transactions,
            'count': len(transactions)
        }
    })

@blockchain_api.route('/transaction/monitor/check/<signature>', methods=['POST'])
@handle_api_errors
def force_check_transaction(signature):
    """强制检查特定交易"""
    result = transaction_monitor.force_check_transaction(signature)
    
    return jsonify({
        'success': 'error' not in result,
        'data': result
    })

@blockchain_api.route('/transaction/rollback/history', methods=['GET'])
@handle_api_errors
def get_rollback_history():
    """获取回滚历史"""
    limit = request.args.get('limit', 100, type=int)
    history = rollback_manager.get_rollback_history(limit)
    
    return jsonify({
        'success': True,
        'data': {
            'history': history,
            'count': len(history)
        }
    })

@blockchain_api.route('/transaction/manager/pending', methods=['GET'])
@handle_api_errors
def get_pending_transactions():
    """获取待处理交易"""
    pending = transaction_manager.get_pending_transactions()
    
    return jsonify({
        'success': True,
        'data': pending
    })

@blockchain_api.route('/system/status', methods=['GET'])
@handle_api_errors
def get_system_status():
    """获取系统整体状态"""
    # 网络健康状态
    network_health = get_network_health_report()
    network_metrics = get_connection_metrics()
    
    # 交易监控统计
    monitor_stats = transaction_monitor.get_monitoring_statistics()
    
    # 待处理交易
    pending_transactions = transaction_manager.get_pending_transactions()
    
    # 回滚历史
    rollback_history = rollback_manager.get_rollback_history(10)
    
    return jsonify({
        'success': True,
        'data': {
            'network': {
                'health': network_health,
                'metrics': network_metrics
            },
            'monitoring': monitor_stats,
            'pending_transactions': pending_transactions,
            'recent_rollbacks': rollback_history,
            'system_time': transaction_monitor.get_monitoring_statistics()['last_updated']
        }
    })

@blockchain_api.route('/deploy_asset', methods=['POST'])
@handle_api_errors
def deploy_asset():
    """部署资产智能合约"""
    data = request.get_json()
    if not data:
        return create_error_response('INVALID_REQUEST', '无效的请求数据')

    asset_id = data.get('asset_id')
    blockchain = data.get('blockchain', 'solana')
    
    if not asset_id:
        return create_error_response('VALIDATION_ERROR', '缺少资产ID', field='asset_id')
    
    asset = Asset.query.get(asset_id)
    if not asset:
        return create_error_response('ASSET_NOT_FOUND', f'资产 {asset_id} 不存在')
    
    if asset.contract_address:
        return jsonify({
            'success': True, 
            'contract_address': asset.contract_address,
            'message': '智能合约已部署'
        })
    
    if blockchain == 'solana':
        asset_service = AssetService()
        logger.info(f"开始部署资产智能合约到Solana: 资产ID={asset_id}")
        deployment_result = asset_service.deploy_asset_to_blockchain(asset_id)
        
        if deployment_result.get('success', False):
            return jsonify({
                'success': True,
                'contract_address': deployment_result.get('token_address'),
                'tx_hash': deployment_result.get('tx_hash'),
                'message': '智能合约部署成功',
                'details': deployment_result.get('details', {})
            })
        else:
            error_msg = deployment_result.get('error', '部署失败')
            logger.error(f"智能合约部署失败: 资产ID={asset_id}, 错误={error_msg}")
            logger.error(f"完整的部署结果: {deployment_result}")
            return create_error_response('CONTRACT_DEPLOYMENT_FAILED', f'部署失败: {error_msg}')
    else:
        return create_error_response('UNSUPPORTED_BLOCKCHAIN', '暂不支持该区块链')

@blockchain_api.route('/solana/check-transaction', methods=['GET'])
@handle_api_errors
def solana_check_transaction():
    """检查Solana交易状态"""
    signature = request.args.get('signature')
    if not signature:
        return create_error_response('VALIDATION_ERROR', '缺少交易签名', field='signature')

    try:
        status = check_transaction_status(signature)
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"检查交易状态失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f'检查交易状态失败: {str(e)}')

# 启动交易监控服务
@blockchain_api.before_app_request
def start_monitoring_services():
    """启动监控服务"""
    try:
        transaction_monitor.start_monitoring()
        logger.info("交易监控服务已启动")
    except Exception as e:
        logger.error(f"启动交易监控服务失败: {e}")