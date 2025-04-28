from flask import Blueprint, jsonify, request, g, current_app, session, url_for, flash, redirect, render_template, abort
import json
import os
import uuid
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import or_, and_, func, desc
import traceback

# 创建蓝图
api_bp = Blueprint('api', __name__)

@api_bp.route('/assets/list', methods=['GET'])
def list_assets():
    """获取资产列表"""
    try:
        current_app.logger.info("请求资产列表")
        return jsonify([]), 200
    except Exception as e:
        current_app.logger.error(f"获取资产列表失败: {str(e)}")
        return jsonify([]), 200

@api_bp.route('/user/assets', methods=['GET'])
def get_user_assets_query():
    """获取用户持有的资产数据（通过查询参数）"""
    try:
        # 从查询参数获取地址
        address = request.args.get('address')
        wallet_type = request.args.get('wallet_type', 'ethereum')
        
        if not address:
            return jsonify({'success': False, 'error': '缺少钱包地址'}), 400
            
        # 记录当前请求的钱包地址，用于调试
        current_app.logger.info(f'通过查询参数获取资产 - 地址: {address}, 类型: {wallet_type}')
        
        # 查询用户
        from app.models.asset import Asset
        from app.models.holding import Holding
        from app.models.user import User
        from app.models.trade import Trade, TradeStatus
        from sqlalchemy import or_
        
        user = None
        try:
            # 尝试查找用户 - 兼容不同地址大小写
            if wallet_type.lower() == 'ethereum':  # 以太坊地址
                # 查询用户 - 同时匹配原始大小写和小写地址
                user = User.query.filter(
                    or_(
                        User.eth_address == address,
                        User.eth_address == address.lower()
                    )
                ).first()
            else:  # Solana地址或其他类型
                user = User.query.filter_by(sol_address=address).first()
        except Exception as e:
            current_app.logger.error(f'查询用户失败: {str(e)}')
            
        # 如果找不到用户，尝试使用交易记录方式查询
        if not user:
            current_app.logger.info(f'未找到用户: {address}，尝试使用交易记录查询')
        
            try:
                # 根据地址类型处理
                if wallet_type.lower() == 'ethereum':
                    # ETH地址，查询原始大小写地址和小写地址
                    completed_trades = Trade.query.filter(
                        Trade.trader_address.in_([address, address.lower()]),
                        Trade.status == TradeStatus.COMPLETED.value
                    ).all()
                else:
                    # SOL地址或其他类型，查询原始地址（区分大小写）
                    completed_trades = Trade.query.filter_by(
                        trader_address=address,
                        status=TradeStatus.COMPLETED.value
                    ).all()
                
                # 按资产ID分组
                assets_holdings = {}
                for trade in completed_trades:
                    asset_id = trade.asset_id
                    
                    if asset_id not in assets_holdings:
                        assets_holdings[asset_id] = {
                            'asset_id': asset_id,
                            'holding_amount': 0,
                            'total_value': 0,
                            'trades': []
                        }
                    
                    # 根据交易类型增加或减少持有量
                    if trade.type == 'buy':
                        assets_holdings[asset_id]['holding_amount'] += trade.amount
                        assets_holdings[asset_id]['total_value'] += float(trade.total or (trade.amount * trade.price))
                    elif trade.type == 'sell':
                        assets_holdings[asset_id]['holding_amount'] -= trade.amount
                        assets_holdings[asset_id]['total_value'] -= float(trade.total or (trade.amount * trade.price))
                    
                    assets_holdings[asset_id]['trades'].append(trade)
            
                # 获取资产详情并组装返回数据
                user_assets = []
                for asset_id, holding_data in assets_holdings.items():
                    # 只返回持有量大于0的资产
                    if holding_data['holding_amount'] <= 0:
                        continue
                        
                    try:
                        asset = Asset.query.get(asset_id)
                        if not asset:
                            continue
                        
                        # 处理图片URL
                        image_url = None
                        if hasattr(asset, 'images') and asset.images:
                            try:
                                # 解析JSON字符串
                                if isinstance(asset.images, str):
                                    images = json.loads(asset.images)
                                    if images and len(images) > 0:
                                        image_url = images[0]
                                # 已经是列表的情况
                                elif isinstance(asset.images, list) and len(asset.images) > 0:
                                    image_url = asset.images[0]
                            except Exception as e:
                                current_app.logger.error(f'解析图片URL失败: {e}')
                                # 如果解析失败，尝试直接使用
                                if isinstance(asset.images, str) and asset.images.startswith('/'):
                                    image_url = asset.images
                            
                        # 计算平均成本和当前价值
                        avg_cost = holding_data['total_value'] / holding_data['holding_amount'] if holding_data['holding_amount'] > 0 else 0
                        current_value = holding_data['holding_amount'] * float(asset.token_price)
                        
                        user_assets.append({
                            'asset_id': asset_id,
                            'name': asset.name,
                            'image_url': image_url,
                            'token_symbol': asset.token_symbol,
                            'holding_amount': holding_data['holding_amount'],
                            'total_supply': asset.token_supply,
                            'holding_percentage': (holding_data['holding_amount'] / asset.token_supply) * 100 if asset.token_supply > 0 else 0,
                            'avg_cost': round(avg_cost, 6),
                            'current_price': float(asset.token_price),
                            'total_value': current_value,
                            'profit_loss': current_value - holding_data['total_value'],
                            'profit_loss_percentage': ((current_value / holding_data['total_value']) - 1) * 100 if holding_data['total_value'] > 0 else 0
                        })
                    except Exception as asset_error:
                        current_app.logger.error(f'处理资产 {asset_id} 时发生错误: {str(asset_error)}', exc_info=True)
                        continue
                
                # 按持有价值降序排序
                user_assets.sort(key=lambda x: x['total_value'], reverse=True)
                
                current_app.logger.info(f'通过交易记录找到了 {len(user_assets)} 个资产')
                return jsonify(user_assets), 200
            except Exception as trade_error:
                current_app.logger.error(f'通过交易记录查询失败: {str(trade_error)}', exc_info=True)
                return jsonify([]), 200
            
        current_app.logger.info(f'找到用户 ID: {user.id}，查询其资产')
        
        # 查询用户持有的资产
        holdings = Holding.query.filter_by(user_id=user.id).all()
        
        # 如果没有持有资产，返回空数组
        if not holdings:
            current_app.logger.info(f'用户 {user.id} 没有持有资产，返回空数组')
            return jsonify([]), 200
            
        # 准备返回的资产数据
        result = []
        
        for holding in holdings:
            # 查询资产详情
            asset = Asset.query.get(holding.asset_id)
            if not asset:
                continue
                
            # 构建资产数据
            # 安全处理image_url
            image_url = None
            if hasattr(asset, 'images') and asset.images:
                try:
                    # 解析JSON字符串
                    if isinstance(asset.images, str):
                        images = json.loads(asset.images)
                        if images and len(images) > 0:
                            image_url = images[0]
                    # 已经是列表的情况
                    elif isinstance(asset.images, list) and len(asset.images) > 0:
                        image_url = asset.images[0]
                except Exception as e:
                    current_app.logger.error(f'解析图片URL失败: {e}')
                    # 如果解析失败，尝试直接使用
                    if isinstance(asset.images, str) and asset.images.startswith('/'):
                        image_url = asset.images
                
            asset_data = {
                'asset_id': asset.id,
                'name': asset.name,
                'image_url': image_url,
                'token_symbol': asset.token_symbol,
                'holding_amount': holding.quantity,
                'total_supply': asset.token_supply,
                'holding_percentage': (holding.quantity / asset.token_supply) * 100 if asset.token_supply > 0 else 0,
                'avg_cost': float(holding.purchase_price) if holding.purchase_price else 0,
                'current_price': float(asset.token_price),
                'total_value': holding.quantity * float(asset.token_price),
                'profit_loss': (holding.quantity * float(asset.token_price)) - (holding.quantity * float(holding.purchase_price or 0)),
                'profit_loss_percentage': ((float(asset.token_price) / float(holding.purchase_price)) - 1) * 100 if holding.purchase_price and float(holding.purchase_price) > 0 else 0
            }
            result.append(asset_data)
            
        current_app.logger.info(f'返回用户 {user.id} 的 {len(result)} 个资产')
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f'获取用户资产失败: {str(e)}', exc_info=True)
        return jsonify([]), 200

@api_bp.route('/user/assets/<string:address>', methods=['GET'])
def get_user_assets(address):
    """获取用户持有的资产数据（通过路径参数）"""
    try:
        # 记录当前请求的钱包地址，用于调试
        current_app.logger.info(f'通过路径参数获取资产 - 地址: {address}')
        
        # 查询用户
        from app.models.asset import Asset
        from app.models.holding import Holding
        from app.models.user import User
        from app.models.trade import Trade, TradeStatus
        from sqlalchemy import or_
        
        user = None
        try:
            # 尝试查找用户 - 兼容不同地址大小写
            if address.startswith('0x'):  # 以太坊地址
                # 查询用户 - 同时匹配原始大小写和小写地址
                user = User.query.filter(
                    or_(
                        User.eth_address == address,
                        User.eth_address == address.lower()
                    )
                ).first()
            else:  # Solana地址
                user = User.query.filter_by(sol_address=address).first()
        except Exception as e:
            current_app.logger.error(f'查询用户失败: {str(e)}')
            
        # 如果找不到用户，尝试使用交易记录方式查询
        if not user:
            current_app.logger.info(f'未找到用户: {address}，尝试使用交易记录查询')
        
            try:
                # 根据地址类型处理
                if address.startswith('0x'):
                    # ETH地址，查询原始大小写地址和小写地址
                    completed_trades = Trade.query.filter(
                        Trade.trader_address.in_([address, address.lower()]),
                        Trade.status == TradeStatus.COMPLETED.value
                    ).all()
                else:
                    # SOL地址或其他类型，查询原始地址（区分大小写）
                    completed_trades = Trade.query.filter_by(
                        trader_address=address,
                        status=TradeStatus.COMPLETED.value
                    ).all()
                
                # 按资产ID分组
                assets_holdings = {}
                for trade in completed_trades:
                    asset_id = trade.asset_id
                    
                    if asset_id not in assets_holdings:
                        assets_holdings[asset_id] = {
                            'asset_id': asset_id,
                            'holding_amount': 0,
                            'total_value': 0,
                            'trades': []
                        }
                    
                    # 根据交易类型增加或减少持有量
                    if trade.type == 'buy':
                        assets_holdings[asset_id]['holding_amount'] += trade.amount
                        assets_holdings[asset_id]['total_value'] += float(trade.total or (trade.amount * trade.price))
                    elif trade.type == 'sell':
                        assets_holdings[asset_id]['holding_amount'] -= trade.amount
                        assets_holdings[asset_id]['total_value'] -= float(trade.total or (trade.amount * trade.price))
                    
                    assets_holdings[asset_id]['trades'].append(trade)
                
                # 获取资产详情并组装返回数据
                user_assets = []
                for asset_id, holding_data in assets_holdings.items():
                    # 只返回持有量大于0的资产
                    if holding_data['holding_amount'] <= 0:
                        continue
                        
                    try:
                        asset = Asset.query.get(asset_id)
                        if not asset:
                            continue
                        
                        # 处理图片URL
                        image_url = None
                        if hasattr(asset, 'images') and asset.images:
                            try:
                                # 解析JSON字符串
                                if isinstance(asset.images, str):
                                    images = json.loads(asset.images)
                                    if images and len(images) > 0:
                                        image_url = images[0]
                                # 已经是列表的情况
                                elif isinstance(asset.images, list) and len(asset.images) > 0:
                                    image_url = asset.images[0]
                            except Exception as e:
                                current_app.logger.error(f'解析图片URL失败: {e}')
                                # 如果解析失败，尝试直接使用
                                if isinstance(asset.images, str) and asset.images.startswith('/'):
                                    image_url = asset.images
                            
                        # 计算平均成本和当前价值
                        avg_cost = holding_data['total_value'] / holding_data['holding_amount'] if holding_data['holding_amount'] > 0 else 0
                        current_value = holding_data['holding_amount'] * float(asset.token_price)
                        
                        user_assets.append({
                            'asset_id': asset_id,
                            'name': asset.name,
                            'image_url': image_url,
                            'token_symbol': asset.token_symbol,
                            'holding_amount': holding_data['holding_amount'],
                            'total_supply': asset.token_supply,
                            'holding_percentage': (holding_data['holding_amount'] / asset.token_supply) * 100 if asset.token_supply > 0 else 0,
                            'avg_cost': round(avg_cost, 6),
                            'current_price': float(asset.token_price),
                            'total_value': current_value,
                            'profit_loss': current_value - holding_data['total_value'],
                            'profit_loss_percentage': ((current_value / holding_data['total_value']) - 1) * 100 if holding_data['total_value'] > 0 else 0
                        })
                    except Exception as asset_error:
                        current_app.logger.error(f'处理资产 {asset_id} 时发生错误: {str(asset_error)}', exc_info=True)
                        continue
                
                # 按持有价值降序排序
                user_assets.sort(key=lambda x: x['total_value'], reverse=True)
                
                current_app.logger.info(f'通过交易记录找到了 {len(user_assets)} 个资产')
                return jsonify(user_assets), 200
            except Exception as trade_error:
                current_app.logger.error(f'通过交易记录查询失败: {str(trade_error)}', exc_info=True)
                return jsonify([]), 200
            
        current_app.logger.info(f'找到用户 ID: {user.id}，查询其资产')
        
        # 查询用户持有的资产
        holdings = Holding.query.filter_by(user_id=user.id).all()
        
        # 如果没有持有资产，返回空数组
        if not holdings:
            current_app.logger.info(f'用户 {user.id} 没有持有资产，返回空数组')
            return jsonify([]), 200
            
        # 准备返回的资产数据
        result = []
        
        for holding in holdings:
            # 查询资产详情
            asset = Asset.query.get(holding.asset_id)
            if not asset:
                continue
                
            # 构建资产数据
            # 安全处理image_url
            image_url = None
            if hasattr(asset, 'images') and asset.images:
                try:
                    # 解析JSON字符串
                    if isinstance(asset.images, str):
                        images = json.loads(asset.images)
                        if images and len(images) > 0:
                            image_url = images[0]
                    # 已经是列表的情况
                    elif isinstance(asset.images, list) and len(asset.images) > 0:
                        image_url = asset.images[0]
                except Exception as e:
                    current_app.logger.error(f'解析图片URL失败: {e}')
                    # 如果解析失败，尝试直接使用
                    if isinstance(asset.images, str) and asset.images.startswith('/'):
                        image_url = asset.images
                
            asset_data = {
                'asset_id': asset.id,
                'name': asset.name,
                'image_url': image_url,
                'token_symbol': asset.token_symbol,
                'holding_amount': holding.quantity,
                'total_supply': asset.token_supply,
                'holding_percentage': (holding.quantity / asset.token_supply) * 100 if asset.token_supply > 0 else 0,
                'avg_cost': float(holding.purchase_price) if holding.purchase_price else 0,
                'current_price': float(asset.token_price),
                'total_value': holding.quantity * float(asset.token_price),
                'profit_loss': (holding.quantity * float(asset.token_price)) - (holding.quantity * float(holding.purchase_price or 0)),
                'profit_loss_percentage': ((float(asset.token_price) / float(holding.purchase_price)) - 1) * 100 if holding.purchase_price and float(holding.purchase_price) > 0 else 0
            }
            result.append(asset_data)
            
        current_app.logger.info(f'返回用户 {user.id} 的 {len(result)} 个资产')
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f'获取用户资产失败: {str(e)}', exc_info=True)
        return jsonify([]), 200
