#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
区块链相关API路由
"""

from flask import Blueprint, request, jsonify, current_app
import json
from datetime import datetime

from app.extensions import db
from app.models.asset import Asset, AssetStatus
from app.blockchain.rwa_contract_service import rwa_contract_service

# 创建蓝图
blockchain_bp = Blueprint('blockchain', __name__, url_prefix='/api/blockchain')

@blockchain_bp.route('/deploy_asset', methods=['POST'])
def deploy_asset():
    """
    部署资产到智能合约
    用户签名后调用此API提交已签名的交易
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求数据'
            }), 400
        
        asset_id = data.get('asset_id')
        signed_transaction = data.get('signed_transaction')
        wallet_address = data.get('wallet_address')
        
        if not all([asset_id, signed_transaction, wallet_address]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数：asset_id, signed_transaction, wallet_address'
            }), 400
        
        # 获取资产信息
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({
                'success': False,
                'error': '资产不存在'
            }), 404
        
        # 验证创建者
        if asset.creator_address.lower() != wallet_address.lower():
            return jsonify({
                'success': False,
                'error': '只有资产创建者可以部署智能合约'
            }), 403
        
        # 发送交易到区块链
        result = rwa_contract_service.send_transaction(signed_transaction)
        
        if result['success']:
            # 更新资产状态
            asset.deployment_tx_hash = result['signature']
            asset.status = AssetStatus.DEPLOYING.value  # 设置为部署中状态
            
            # 更新区块链数据
            blockchain_data = json.loads(asset.blockchain_data or '{}')
            blockchain_data['deployment_tx'] = result['signature']
            blockchain_data['deployed_at'] = datetime.utcnow().isoformat()
            asset.blockchain_data = json.dumps(blockchain_data)
            
            db.session.commit()
            
            current_app.logger.info(f"资产 {asset_id} 智能合约部署交易已提交: {result['signature']}")
            
            return jsonify({
                'success': True,
                'transaction_signature': result['signature'],
                'message': '资产正在部署到区块链，请等待确认'
            })
        else:
            return jsonify({
                'success': False,
                'error': f"部署失败: {result.get('error')}"
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"部署资产智能合约失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"部署失败: {str(e)}"
        }), 500

@blockchain_bp.route('/confirm_deployment/<string:signature>', methods=['GET'])
def confirm_deployment(signature):
    """
    确认智能合约部署状态
    """
    try:
        result = rwa_contract_service.confirm_transaction(signature)
        
        if result['success'] and result['confirmed']:
            # 查找相关资产并更新状态
            asset = Asset.query.filter_by(deployment_tx_hash=signature).first()
            if asset:
                asset.status = AssetStatus.ON_CHAIN.value  # 设置为已上链状态
                db.session.commit()
                
                current_app.logger.info(f"资产 {asset.id} 已成功部署到区块链")
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"确认部署状态失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"确认失败: {str(e)}"
        }), 500

@blockchain_bp.route('/prepare_purchase', methods=['POST'])
def prepare_purchase():
    """
    准备资产购买的智能合约交易
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求数据'
            }), 400
        
        asset_id = data.get('asset_id')
        buyer_address = data.get('buyer_address')
        amount = data.get('amount')
        
        if not all([asset_id, buyer_address, amount]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数：asset_id, buyer_address, amount'
            }), 400
        
        # 获取资产信息
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({
                'success': False,
                'error': '资产不存在'
            }), 404
        
        # 检查资产是否已上链
        if asset.status != AssetStatus.ON_CHAIN.value:
            return jsonify({
                'success': False,
                'error': '资产尚未上链，无法购买'
            }), 400
        
        # 检查资产是否有有效的智能合约地址
        if not asset.token_address or not asset.contract_address:
            return jsonify({
                'success': False,
                'error': '资产智能合约地址无效，无法购买'
            }), 400
        
        # 检查剩余供应量
        if asset.remaining_supply < amount:
            return jsonify({
                'success': False,
                'error': f'购买数量超过剩余供应量：{asset.remaining_supply}'
            }), 400
        
        # 创建智能合约购买交易
        result = rwa_contract_service.buy_asset_on_chain(
            buyer_address=buyer_address,
            asset_mint=asset.token_address,
            asset_data_account=asset.contract_address,
            amount=int(amount),
            creator_address=asset.creator_address
        )
        
        if result['success']:
            # 计算购买总价
            total_price = float(asset.token_price) * int(amount)
            platform_fee = total_price * 0.035  # 3.5%平台费
            creator_amount = total_price - platform_fee
            
            return jsonify({
                'success': True,
                'transaction_data': result['transaction_data'],
                'buyer_asset_ata': result['buyer_asset_ata'],
                'buyer_usdc_ata': result['buyer_usdc_ata'],
                'total_price': total_price,
                'platform_fee': platform_fee,
                'creator_amount': creator_amount,
                'asset_info': {
                    'id': asset.id,
                    'name': asset.name,
                    'token_symbol': asset.token_symbol,
                    'token_price': float(asset.token_price),
                    'remaining_supply': asset.remaining_supply
                },
                'message': '购买交易已准备完成，请在钱包中签名'
            })
        else:
            return jsonify({
                'success': False,
                'error': f"准备购买交易失败: {result.get('error')}"
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"准备购买交易失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"准备购买失败: {str(e)}"
        }), 500

@blockchain_bp.route('/execute_purchase', methods=['POST'])
def execute_purchase():
    """
    执行资产购买（提交已签名的智能合约交易）
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求数据'
            }), 400
        
        asset_id = data.get('asset_id')
        buyer_address = data.get('buyer_address')
        amount = data.get('amount')
        signed_transaction = data.get('signed_transaction')
        
        if not all([asset_id, buyer_address, amount, signed_transaction]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400
        
        # 获取资产信息
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({
                'success': False,
                'error': '资产不存在'
            }), 404
        
        # 发送交易到区块链
        result = rwa_contract_service.send_transaction(signed_transaction)
        
        if result['success']:
            # 创建交易记录
            from app.models.trade import Trade, TradeType, TradeStatus
            
            new_trade = Trade(
                asset_id=asset_id,
                type=TradeType.BUY.value,
                amount=int(amount),
                price=float(asset.token_price),
                total=float(asset.token_price) * int(amount),
                trader_address=buyer_address,
                status=TradeStatus.PENDING_CONFIRMATION.value,
                tx_hash=result['signature'],
                payment_details=json.dumps({
                    'method': 'smart_contract',
                    'contract_tx': result['signature'],
                    'timestamp': datetime.utcnow().isoformat()
                })
            )
            
            # 更新资产剩余供应量（临时减少，等待确认）
            asset.remaining_supply = max(0, asset.remaining_supply - int(amount))
            
            db.session.add(new_trade)
            db.session.commit()
            
            current_app.logger.info(f"智能合约购买交易已提交: 资产{asset_id}, 买家{buyer_address}, 交易{result['signature']}")
            
            return jsonify({
                'success': True,
                'transaction_signature': result['signature'],
                'trade_id': new_trade.id,
                'message': '购买交易已提交到区块链，等待确认'
            })
        else:
            return jsonify({
                'success': False,
                'error': f"购买失败: {result.get('error')}"
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"执行购买交易失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"购买失败: {str(e)}"
        }), 500