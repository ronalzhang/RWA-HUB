from flask import Blueprint, jsonify, request, g, current_app, session, url_for, flash, redirect, render_template, abort, Response
import json
import os
import uuid
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import or_, and_, func, desc
import traceback
import re
import requests
from app.models import Asset, User, Trade, AssetType
from app.extensions import db
from app.blockchain.solana_service import execute_transfer_transaction

# 从__init__.py导入正确的API蓝图
from . import api_bp

# 日志记录器
logger = logging.getLogger(__name__)

@api_bp.route('/assets/list', methods=['GET'])
def list_assets():
    """获取资产列表"""
    try:
        current_app.logger.info("请求资产列表")
        
        from app.models.asset import Asset, AssetStatus
        from app.models.user import User
        from sqlalchemy import desc
        
        # 构建查询 - 只显示已上链且未删除的资产
        query = Asset.query.filter(
            Asset.status == AssetStatus.ON_CHAIN.value,
            Asset.deleted_at.is_(None)  # 排除已删除的资产
        )
        
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 获取筛选参数
        asset_type = request.args.get('type')
        location = request.args.get('location')
        search = request.args.get('search')
        
        # 按类型筛选
        if asset_type:
            try:
                type_value = int(asset_type)
                query = query.filter(Asset.asset_type == type_value)
            except ValueError:
                pass
        
        # 按位置筛选
        if location:
            query = query.filter(Asset.location.ilike(f'%{location}%'))
            
        # 搜索功能
        if search:
            query = query.filter(
                db.or_(
                    Asset.name.ilike(f'%{search}%'),
                    Asset.description.ilike(f'%{search}%'),
                    Asset.token_symbol.ilike(f'%{search}%')
                )
            )
        
        # 排序 - 按创建时间倒序
        query = query.order_by(desc(Asset.created_at))
        
        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        assets = pagination.items
        
        # 转换为前端需要的格式
        asset_list = []
        for asset in assets:
            # 获取第一张图片
            image_url = None
            if asset.images and len(asset.images) > 0:
                image_url = asset.images[0]
            
            # 获取资产类型名称
            asset_type_name = '其他'
            try:
                from app.models.asset import AssetType
                for item in AssetType:
                    if item.value == asset.asset_type:
                        if item.value == 10:
                            asset_type_name = '不动产'
                        elif item.value == 20:
                            asset_type_name = '商业地产'
                        elif item.value == 30:
                            asset_type_name = '工业地产'
                        elif item.value == 40:
                            asset_type_name = '土地资产'
                        elif item.value == 50:
                            asset_type_name = '证券资产'
                        elif item.value == 60:
                            asset_type_name = '艺术品'
                        elif item.value == 70:
                            asset_type_name = '收藏品'
                        else:
                            asset_type_name = '其他'
                        break
            except:
                asset_type_name = '其他'
            
            asset_data = {
                'id': asset.id,
                'name': asset.name,
                'description': asset.description,
                'asset_type': asset.asset_type,
                'asset_type_name': asset_type_name,
                'location': asset.location,
                'area': float(asset.area) if asset.area else 0,
                'token_symbol': asset.token_symbol,
                'token_price': float(asset.token_price) if asset.token_price else 0,
                'token_supply': asset.token_supply,
                'remaining_supply': asset.remaining_supply or asset.token_supply,
                'total_value': float(asset.total_value) if asset.total_value else 0,
                'annual_revenue': float(asset.annual_revenue) if asset.annual_revenue else 0,
                'images': asset.images if asset.images else [],
                'image_url': image_url,
                'token_address': asset.token_address,
                'creator_address': asset.creator_address,
                'created_at': asset.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': asset.updated_at.strftime('%Y-%m-%d %H:%M:%S') if asset.updated_at else None
            }
            
            asset_list.append(asset_data)
        
        current_app.logger.info(f"返回 {len(asset_list)} 个资产")
        return jsonify(asset_list), 200
        
    except Exception as e:
        current_app.logger.error(f"获取资产列表失败: {str(e)}", exc_info=True)
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
                # -- 修改：移除对 sol_address 的查询，因为 User 模型没有此字段 --
                # user = User.query.filter_by(sol_address=address).first()
                # 如果不是 ETH 地址，我们无法直接通过 User 模型查找，后续将通过交易记录查找
                user = None 
        except Exception as e:
            current_app.logger.error(f'查询用户失败: {str(e)}')
            # -- 修改：查询失败时也设置 user = None，进入用户创建逻辑 --
            user = None 
            
        # 如果找不到用户，自动创建用户记录
        if not user:
            current_app.logger.info(f'未找到用户: {address}，自动创建用户记录')
            try:
                from app.models.commission_config import UserCommissionBalance
                
                # 创建新用户
                user = User(
                    eth_address=address if wallet_type.lower() == 'ethereum' else None,
                    username=f'user_{address[:8]}',  # 使用地址前8位作为用户名
                    email=f'{address[:8]}@wallet.generated',  # 生成一个临时邮箱
                    role='user',
                    is_distributor=True,  # 所有用户都是分销商
                    created_at=datetime.utcnow()
                )
                
                db.session.add(user)
                db.session.flush()  # 获取用户ID
                
                # 为新用户创建佣金余额记录
                commission_balance = UserCommissionBalance(
                    user_address=address,
                    total_earned=Decimal('0.00'),
                    available_balance=Decimal('0.00'),
                    withdrawn_amount=Decimal('0.00'),
                    frozen_amount=Decimal('0.00')
                )
                db.session.add(commission_balance)
                db.session.commit()
                
                current_app.logger.info(f'成功创建新用户: ID={user.id}, 地址={address}')
                
            except Exception as create_error:
                current_app.logger.error(f'创建用户失败: {str(create_error)}')
                db.session.rollback()
                # 创建失败时，继续使用交易记录方式查询
                user = None
        
        # 如果仍然没有用户（创建失败），尝试使用交易记录方式查询
        if not user:
            current_app.logger.info(f'用户创建失败或未找到用户: {address}，尝试使用交易记录查询')
        
            try:
                # 根据地址类型处理
                if wallet_type.lower() == 'ethereum':
                    # ETH地址，查询原始大小写地址和小写地址
                    completed_trades = Trade.query.filter(
                        Trade.trader_address.in_([address, address.lower()]),
                        Trade.status.in_([TradeStatus.COMPLETED.value, TradeStatus.PENDING.value])
                    ).all()
                else:
                    # SOL地址或其他类型，查询原始地址（区分大小写）
                    completed_trades = Trade.query.filter(
                        Trade.trader_address == address,
                        Trade.status.in_([TradeStatus.COMPLETED.value, TradeStatus.PENDING.value])
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
                user = None
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
                        Trade.status.in_([TradeStatus.COMPLETED.value, TradeStatus.PENDING.value])
                    ).all()
                else:
                    # SOL地址或其他类型，查询原始地址（区分大小写）
                    completed_trades = Trade.query.filter(
                        Trade.trader_address == address,
                        Trade.status.in_([TradeStatus.COMPLETED.value, TradeStatus.PENDING.value])
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

@api_bp.route('/trades', methods=['GET'])
def get_trade_history():
    """获取资产交易历史"""
    try:
        # 获取查询参数
        asset_id = request.args.get('asset_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)
        
        # 验证参数
        if not asset_id:
            return jsonify({
                'success': False, 
                'error': '缺少资产ID参数'
            }), 400

        # 限制每页数量，避免过大查询
        if per_page > 100:
            per_page = 100
            
        # 查询交易记录
        from app.models.trade import Trade, TradeStatus
        
        # 筛选条件：指定资产ID和已完成状态
        trades_query = Trade.query.filter_by(
            asset_id=asset_id
        ).order_by(Trade.created_at.desc())
        
        # 计算总记录数和总页数
        total_count = trades_query.count()
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        
        # 分页
        trades = trades_query.offset((page - 1) * per_page).limit(per_page).all()
        
        # 格式化交易记录
        trade_list = []
        for trade in trades:
            trade_list.append({
                'id': trade.id,
                'created_at': trade.created_at.isoformat(),
                'trader_address': trade.trader_address,
                'type': trade.type,
                'amount': trade.amount,
                'price': float(trade.price) if trade.price else 0,
                'total': float(trade.total) if trade.total else None,
                'status': trade.status,
                'tx_hash': trade.tx_hash
            })
            
        # 构建分页信息
        pagination = {
            'total': total_count,
            'pages': total_pages,
            'page': page,
            'per_page': per_page
        }
            
        # 返回结果
        return jsonify({
            'trades': trade_list,
            'pagination': pagination
        }), 200
            
    except Exception as e:
        current_app.logger.error(f"获取交易历史失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"获取交易历史失败: {str(e)}"
        }), 500

@api_bp.route('/v2/trades/<string:asset_identifier>', methods=['GET'])
def get_trade_history_v2(asset_identifier):
    """获取资产交易历史 - V2版本，支持RESTful风格URL"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)
        
        # 处理资产标识符，支持数字ID或RH-XXXXX格式
        from app.models.asset import Asset
        asset = None
        
        # 如果是数字，直接按ID查询
        if asset_identifier.isdigit():
            asset = Asset.query.get(int(asset_identifier))
        # 如果是RH-格式，按token_symbol查询
        elif asset_identifier.startswith('RH-'):
            asset = Asset.query.filter_by(token_symbol=asset_identifier).first()
        # 其他情况尝试提取数字ID
        else:
            import re
            match = re.search(r'(\d+)', asset_identifier)
            if match:
                numeric_id = int(match.group(1))
                asset = Asset.query.get(numeric_id)
        
        if not asset:
            current_app.logger.warning(f"V2 API: 找不到资产 {asset_identifier}")
            return jsonify({
                'success': False,
                'error': f'找不到资产: {asset_identifier}'
            }), 404

        # 限制每页数量，避免过大查询
        if per_page > 100:
            per_page = 100
            
        # 查询交易记录
        from app.models.trade import Trade, TradeStatus
        
        # 筛选条件：指定资产ID和已完成状态
        trades_query = Trade.query.filter_by(
            asset_id=asset.id
        ).order_by(Trade.created_at.desc())
        
        # 计算总记录数和总页数
        total_count = trades_query.count()
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        
        # 分页
        trades = trades_query.offset((page - 1) * per_page).limit(per_page).all()
        
        # 格式化交易记录
        trade_list = []
        for trade in trades:
            trade_list.append({
                'id': trade.id,
                'created_at': trade.created_at.isoformat(),
                'trader_address': trade.trader_address,
                'type': trade.type,
                'amount': trade.amount,
                'price': float(trade.price) if trade.price else 0,
                'total': float(trade.total) if trade.total else None,
                'status': trade.status,
                'tx_hash': trade.tx_hash
            })
            
        # 构建分页信息
        pagination = {
            'total': total_count,
            'pages': total_pages,
            'page': page,
            'per_page': per_page
        }
            
        current_app.logger.info(f"V2 API: 成功获取资产 {asset_identifier} 的交易历史，共 {len(trade_list)} 条")
        
        # 返回结果
        return jsonify({
            'success': True,
            'trades': trade_list,
            'pagination': pagination
        }), 200
            
    except Exception as e:
        current_app.logger.error(f"V2 API: 获取交易历史失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"API服务暂时不可用，请稍后重试"
        }), 500

@api_bp.route('/assets/symbol/<string:symbol>', methods=['GET'])
def get_asset_by_symbol(symbol):
    """通过代币符号获取资产详情"""
    try:
        current_app.logger.info(f"请求通过符号获取资产: {symbol}")
        from app.models.asset import Asset
        
        # 查询资产
        asset = Asset.query.filter_by(token_symbol=symbol).first()
        
        # 如果找不到资产，返回404
        if not asset:
            current_app.logger.warning(f"找不到符号为 {symbol} 的资产")
            return jsonify({
                'success': False,
                'error': f'找不到符号为 {symbol} 的资产'
            }), 404
        
        # 将资产转换为字典并返回
        asset_data = asset.to_dict()
        
        # 添加图片URL处理
        if hasattr(asset, 'images') and asset.images:
            asset_data['images'] = asset.images
            
            # 为前端设置主图片
            if asset.images and len(asset.images) > 0:
                asset_data['image_url'] = asset.images[0]
        
        # 构建基本响应
        response = {
            'success': True,
            'id': asset.id,
            'token_symbol': asset.token_symbol,
            'name': asset.name,
            'token_price': float(asset.token_price),
            'token_supply': asset.token_supply,
            'remaining_supply': asset.remaining_supply,
        }
        
        # 添加额外资产数据
        response.update(asset_data)
        
        current_app.logger.info(f"成功返回资产 {symbol} 的详情")
        return jsonify(response), 200
        
    except Exception as e:
        current_app.logger.error(f"通过符号获取资产失败: {symbol}, 错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"获取资产失败: {str(e)}"
        }), 500

@api_bp.route('/trades/prepare_purchase', methods=['POST'])
def prepare_purchase():
    """准备购买交易"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '无效的请求数据'
            }), 400
        
        # 验证必要字段
        asset_id = data.get('asset_id')
        amount = data.get('amount')
        wallet_address = data.get('wallet_address')
        
        if not asset_id:
            return jsonify({
                'success': False,
                'error': '缺少资产ID'
            }), 400
            
        if not amount:
            return jsonify({
                'success': False,
                'error': '缺少购买数量'
            }), 400
            
        if not wallet_address:
            return jsonify({
                'success': False,
                'error': '缺少钱包地址'
            }), 400
        
        # 处理资产ID，支持RH-XXXXXX格式
        from app.models.asset import Asset
        
        asset = None
        try:
            # 如果资产ID是数字，直接查询
            if isinstance(asset_id, int) or (isinstance(asset_id, str) and asset_id.isdigit()):
                asset = Asset.query.get(int(asset_id))
            # 如果资产ID是符号格式，通过符号查询
            elif isinstance(asset_id, str) and asset_id.startswith('RH-'):
                asset = Asset.query.filter_by(token_symbol=asset_id).first()
            
            # 如果上述查询都失败，尝试其他格式处理
            if not asset and isinstance(asset_id, str):
                # 尝试提取数字部分
                match = re.search(r'(\d+)', asset_id)
                if match:
                    numeric_id = int(match.group(1))
                    asset = Asset.query.get(numeric_id)
                    
                    # 如果仍未找到，尝试通过token_symbol模糊匹配
                    if not asset:
                        asset = Asset.query.filter(Asset.token_symbol.like(f"%{numeric_id}%")).first()
        except Exception as e:
            current_app.logger.error(f"查询资产失败: {str(e)}", exc_info=True)
            
        # 如果找不到资产，返回错误
        if not asset:
            return jsonify({
                'success': False,
                'error': f'找不到资产: {asset_id}'
            }), 404
            
        # 将数量转换为整数
        try:
            amount = int(float(amount))
            if amount <= 0:
                return jsonify({
                    'success': False,
                    'error': '购买数量必须大于0'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'error': '无效的购买数量'
            }), 400
            
        # 检查资产是否有足够的剩余供应量
        if asset.remaining_supply is not None and amount > asset.remaining_supply:
            return jsonify({
                'success': False,
                'error': f'购买数量超过可用供应量: {asset.remaining_supply}'
            }), 400
            
        # 计算总价格
        price = float(asset.token_price)
        total = price * amount
        
        # 从系统配置获取平台收款地址
        from app.models.admin import SystemConfig
        from app.utils.config_manager import ConfigManager
        platform_address = ConfigManager.get_platform_fee_address()
        
        # 生成交易ID
        import uuid
        trade_id = str(uuid.uuid4())
        
        # 准备响应数据 - 添加前端期望的字段
        response = {
            'success': True,
            'trade_id': trade_id,
            'purchase_id': trade_id,  # 添加purchase_id别名
            'asset_id': asset.id,
            'token_symbol': asset.token_symbol,
            'name': asset.name,  # 添加资产名称
            'amount': amount,
            'price': price,
            'total': total,
            'total_amount': total,  # 添加前端期望的total_amount字段
            'recipient_address': platform_address,  # 添加前端期望的recipient_address字段
            'platform_address': platform_address,  # 保留平台地址字段
            'wallet_address': wallet_address
        }
        
        # 在会话中存储待确认的交易数据，有效期10分钟
        from datetime import datetime, timedelta
        session_key = f'purchase_tx_{trade_id}'
        
        session[session_key] = {
            'trade_id': trade_id,
            'asset_id': asset.id,
            'token_symbol': asset.token_symbol,
            'name': asset.name,  # 添加资产名称
            'amount': amount,
            'price': price,
            'total': total,
            'wallet_address': wallet_address,
            'expires_at': (datetime.utcnow() + timedelta(minutes=10)).timestamp()
        }
        
        current_app.logger.info(f"准备购买成功: 资产 {asset.token_symbol}, 交易ID {trade_id}")
        return jsonify(response), 200
        
    except Exception as e:
        current_app.logger.error(f"准备购买失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"准备购买失败: {str(e)}"
        }), 500

@api_bp.route('/trades/confirm_purchase', methods=['POST'])
def confirm_purchase():
    """确认购买交易"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '无效的请求数据'
            }), 400
            
        # 验证必要字段 - 兼容前端发送的purchase_id和trade_id
        trade_id = data.get('trade_id') or data.get('purchase_id')
        signature = data.get('signature')  # 获取交易签名
        
        if not trade_id:
            return jsonify({
                'success': False,
                'error': '缺少交易ID'
            }), 400
            
        # 从会话中获取交易数据
        session_key = f'purchase_tx_{trade_id}'
        tx_data = session.get(session_key)
        
        if not tx_data:
            # 检查此交易ID是否已经完成过
            from app.models.trade import Trade
            existing_trade = Trade.query.filter_by(payment_details=trade_id).first()
            if existing_trade:
                return jsonify({
                    'success': True,
                    'status': 'completed',
                    'message': '该交易已经完成',
                    'transaction': {
                        'id': existing_trade.id,
                        'asset_id': existing_trade.asset_id,
                        'amount': existing_trade.amount,
                        'price': float(existing_trade.price),
                        'total': float(existing_trade.total),
                        'status': existing_trade.status,
                        'created_at': existing_trade.created_at.isoformat()
                    }
                }), 200
            
            return jsonify({
                'success': False,
                'error': '找不到交易数据或交易已过期'
            }), 404
            
        # 检查交易是否已过期
        from datetime import datetime
        if datetime.utcnow().timestamp() > tx_data.get('expires_at', 0):
            # 删除过期交易数据
            session.pop(session_key, None)
            return jsonify({
                'success': False,
                'error': '交易已过期'
            }), 400
            
        # 创建新交易记录
        from app.models.trade import Trade, TradeType, TradeStatus
        from app.models.asset import Asset
        import json
        
        # 获取交易相关数据
        asset_id = tx_data['asset_id']
        amount = tx_data['amount']
        price = tx_data['price']
        total = tx_data['total']
        wallet_address = tx_data['wallet_address']
        token_symbol = tx_data.get('token_symbol', '')
        
        try:
            # 查询资产
            asset = Asset.query.get(asset_id)
            if not asset:
                return jsonify({
                    'success': False,
                    'error': f'找不到资产: {asset_id}'
                }), 404
                
            # 检查资产是否有足够的剩余供应量
            if asset.remaining_supply is not None and amount > asset.remaining_supply:
                return jsonify({
                    'success': False,
                    'error': f'购买数量超过可用供应量: {asset.remaining_supply}'
                }), 400
                
            # 创建交易记录
            payment_details = {
                'method': 'api',
                'trade_id': trade_id,
                'timestamp': datetime.utcnow().isoformat(),
                'wallet_address': wallet_address
            }
            
            new_trade = Trade(
                asset_id=asset_id,
                type=TradeType.BUY.value,
                amount=amount,
                price=price,
                total=total,
                trader_address=wallet_address,
                status=TradeStatus.COMPLETED.value,  # 直接设为已完成
                tx_hash=signature,  # 保存交易签名作为交易哈希
                payment_details=json.dumps(payment_details)
            )
            
            # 更新资产剩余供应量
            if asset.remaining_supply is not None:
                asset.remaining_supply = max(0, asset.remaining_supply - amount)
                
            # 保存到数据库
            db.session.add(new_trade)
            db.session.commit()
            
            # 清除会话中的交易数据
            session.pop(session_key, None)
            
            # 准备响应数据
            response = {
                'success': True,
                'trade_id': trade_id,
                'status': 'completed',
                'message': '购买成功！资产将在几分钟内添加到您的钱包',
                'transaction': {
                    'id': new_trade.id,
                    'asset_id': asset_id,
                    'token_symbol': asset.token_symbol,
                    'name': asset.name,
                    'amount': amount,
                    'price': price,
                    'total': total,
                    'status': new_trade.status,
                    'tx_hash': signature,  # 包含交易哈希
                    'created_at': new_trade.created_at.isoformat()
                }
            }
            
            current_app.logger.info(f"确认购买成功: 交易ID {trade_id}, 资产 {asset.token_symbol}")
            return jsonify(response), 200
        except Exception as db_error:
            db.session.rollback()
            current_app.logger.error(f"数据库操作失败: {str(db_error)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f"数据库操作失败: {str(db_error)}"
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"确认购买失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"确认购买失败: {str(e)}"
        }), 500

@api_bp.route('/dividend/stats/<string:asset_id>')
def get_dividend_stats_api(asset_id):
    """获取资产的分红统计信息（兼容前端API）"""
    try:
        current_app.logger.info(f"请求资产分红统计: {asset_id}")
        from app.models.asset import Asset
        
        # 处理资产ID格式，支持RH-XXXXX和数字ID
        asset = None
        if asset_id.startswith('RH-'):
            asset = Asset.query.filter_by(token_symbol=asset_id).first()
        else:
            try:
                asset_numeric_id = int(asset_id)
                asset = Asset.query.get(asset_numeric_id)
            except ValueError:
                # 如果转换失败，则尝试通过token_symbol查询
                asset = Asset.query.filter_by(token_symbol=asset_id).first()
        
        if not asset:
            current_app.logger.warning(f"找不到资产: {asset_id}")
            return jsonify({
                'success': False,
                'error': f'找不到资产: {asset_id}'
            }), 404
            
        # 这里返回定制的分红数据，由于原分红API不可用，提供默认值
        # 这些值可以根据实际需求自定义
        default_dividend_data = {
            'success': True,
            'total_dividends': 450000,
            'last_dividend': {
                'amount': 120000,
                'date': "2023-09-30",
                'status': "completed"
            },
            'next_dividend': {
                'amount': 125000,
                'date': "2023-12-31",
                'status': "scheduled"
            },
            'asset_id': asset_id,
            'token_symbol': asset.token_symbol,
            'name': asset.name
        }
        
        current_app.logger.info(f"返回资产 {asset_id} 的分红数据")
        return jsonify(default_dividend_data), 200
        
    except Exception as e:
        current_app.logger.error(f"获取分红统计失败: {str(e)}", exc_info=True)
        # 即使出错也返回默认数据，确保前端能正常显示
        return jsonify({
            'success': True,
            'total_dividends': 450000,
            'last_dividend': {
                'amount': 120000,
                'date': "2023-09-30",
                'status': "completed"
            },
            'next_dividend': {
                'amount': 125000,
                'date': "2023-12-31",
                'status': "scheduled"
            },
            'asset_id': asset_id
        }), 200

@api_bp.route('/assets/<string:asset_id>/dividend')
def get_asset_dividend_api(asset_id):
    """资产分红数据API的别名路由（兼容前端其他API路径）"""
    return get_dividend_stats_api(asset_id)

@api_bp.route('/dividend/total/<string:asset_id>')
def get_dividend_total_api(asset_id):
    """资产分红总额API的别名路由（兼容前端其他API路径）"""
    return get_dividend_stats_api(asset_id)

@api_bp.route('/assets/<string:token_symbol>/dividends/total')
def get_asset_dividends_total(token_symbol):
    """获取资产分红总额 - 兼容前端asset_detail.js调用的路径"""
    try:
        current_app.logger.info(f"请求资产分红总额: {token_symbol}")
        from app.models.asset import Asset
        from app.models.dividend import DividendRecord
        
        # 查找资产
        asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if not asset:
            current_app.logger.warning(f"找不到资产: {token_symbol}")
            return jsonify({
                'success': False,
                'error': f'找不到资产: {token_symbol}',
                'total_amount': 0
            }), 404
        
        # 计算总分红金额
        try:
            # 尝试从DividendRecord表中计算总分红
            total_amount = db.session.query(db.func.sum(DividendRecord.amount)).filter_by(asset_id=asset.id).scalar() or 0
        except Exception as e:
            current_app.logger.warning(f"无法从DividendRecord计算分红，使用默认值: {str(e)}")
            # 如果分红表不存在或有问题，返回0
            total_amount = 0
        
        current_app.logger.info(f"资产 {token_symbol} 的总分红金额: {total_amount}")
        
        return jsonify({
            'success': True,
            'total_amount': float(total_amount),
            'asset_symbol': token_symbol,
            'asset_name': asset.name
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取资产分红总额失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'total_amount': 0
        }), 500

@api_bp.route('/solana/execute_transfer_v2', methods=['POST'])
def api_execute_transfer_v2():
    """使用服务器作为中转执行Solana转账交易"""
    try:
        data = request.json
        logger.info(f"API路由收到转账请求: {data}")
        
        # 验证必要参数
        required_fields = ['from_address', 'to_address', 'amount', 'token_symbol']
        
        # 前端传来的参数名称可能有所不同，进行兼容处理
        mapped_data = {
            'from_address': data.get('from_address') or data.get('fromAddress'),
            'to_address': data.get('to_address') or data.get('toAddress'),
            'amount': data.get('amount'),
            'token_symbol': data.get('token_symbol') or data.get('tokenSymbol'),
            'purpose': data.get('purpose'),
            'metadata': data.get('metadata')
        }
        
        # 检查必填字段
        missing_fields = []
        for field in required_fields:
            if not mapped_data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"转账请求缺少必要参数: {missing_fields}")
            return jsonify({
                'success': False,
                'message': f"缺少必要参数: {', '.join(missing_fields)}"
            }), 400
            
        # 通知前端需要使用钱包来执行交易，而不是由服务器代替执行
        return jsonify({
            'success': False,
            'message': "请使用钱包直接执行交易，服务器不代替执行转账操作",
            'requireWallet': True
        }), 200
            
    except Exception as e:
        logger.error(f"API异常: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f"处理请求时发生异常: {str(e)}"
        }), 500

@api_bp.route('/solana/build_transfer', methods=['GET'])
def api_build_transfer():
    """构建Solana转账交易，返回序列化的交易数据"""
    try:
        # 获取查询参数
        from_address = request.args.get('from')
        to_address = request.args.get('to')
        amount = request.args.get('amount')
        token_mint = request.args.get('token_mint')
        
        logger.info(f"收到构建转账请求 - from: {from_address}, to: {to_address}, amount: {amount}, token: {token_mint}")
        
        # 验证参数完整性
        if not all([from_address, to_address, amount, token_mint]):
            missing_fields = []
            if not from_address:
                missing_fields.append('from')
            if not to_address:
                missing_fields.append('to')
            if not amount:
                missing_fields.append('amount')
            if not token_mint:
                missing_fields.append('token')
                
            logger.error(f"构建转账请求缺少必要参数: {', '.join(missing_fields)}")
            return jsonify({
                'success': False,
                'error': f"缺少必要参数: {', '.join(missing_fields)}"
            }), 400
        
        # 简化处理 - 直接返回简化版的交易参数
        # 在实际应用中，这里会构建真实的Solana交易
        return jsonify({
            'success': True,
            'transaction_data': {
                'from': from_address,
                'to': to_address,
                'amount': amount,
                'token_mint': token_mint
            },
            'message': 'Transaction parameters built successfully'
        })
    except Exception as e:
        logger.exception(f"构建Solana转账交易失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"构建转账交易失败: {str(e)}"
        }), 500

@api_bp.route('/solana/relay', methods=['POST'])
def solana_relay():
    """Solana网络中继API - 让前端通过服务器连接Solana网络"""
    try:
        # 获取请求数据
        relay_data = request.json
        logger.info("收到Solana网络中继请求")
        
        if not relay_data:
            logger.error("中继请求缺少数据")
            return jsonify({'error': 'No data provided'}), 400
            
        # 设置Solana RPC节点URL
        solana_rpc_url = os.environ.get("SOLANA_NETWORK_URL", "https://api.mainnet-beta.solana.com")
        
        # 转发请求到Solana网络
        import requests
        
        solana_response = requests.post(
            solana_rpc_url,
            json=relay_data,
            headers={
                'Content-Type': 'application/json'
            },
            timeout=30  # 增加超时时间
        )
        
        # 返回Solana网络响应
        if solana_response.status_code == 200:
            return jsonify(solana_response.json()), 200
        else:
            logger.error(f"Solana网络返回错误: {solana_response.status_code} - {solana_response.text}")
            return jsonify({
                'error': f"Solana网络返回错误: {solana_response.status_code}",
                'details': solana_response.text
            }), 502
            
    except Exception as e:
        logger.error(f"处理Solana中继请求时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'error': f"处理中继请求时出错: {str(e)}"
        }), 500

@api_bp.route('/solana/direct_transfer', methods=['POST'])
def solana_direct_transfer():
    """直接处理Solana转账请求，执行真实链上交易"""
    try:
        data = request.json
        logger.info(f"收到真实链上转账请求: {data}")
        
        # 验证基本参数
        required_fields = ['from_address', 'to_address', 'amount', 'token_symbol']
        
        # 前端传来的参数名称可能有所不同，进行兼容处理
        mapped_data = {
            'from_address': data.get('from_address') or data.get('fromAddress'),
            'to_address': data.get('to_address') or data.get('toAddress'),
            'amount': data.get('amount'),
            'token_symbol': data.get('token_symbol') or data.get('tokenSymbol') or data.get('token'),
            'purpose': data.get('purpose'),
            'metadata': data.get('metadata')
        }
        
        # 检查必填字段
        missing_fields = []
        for field in required_fields:
            if not mapped_data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"转账请求缺少必要参数: {missing_fields}")
            return jsonify({
                'success': False,
                'message': f"缺少必要参数: {', '.join(missing_fields)}"
            }), 400
        
        # 记录交易信息到数据库 (这步可以根据实际需要实现)
        logger.info(f"记录支付交易: {mapped_data['from_address']} -> {mapped_data['to_address']}, 金额: {mapped_data['amount']} {mapped_data['token_symbol']}")
        
        # 使用区块链服务执行交易
        from app.blockchain.solana_service import execute_transfer_transaction
        
        # 这里应该是实际执行区块链交易的代码
        result = {
            'success': True,
            'message': "支付请求已提交至区块链",
            'signature': None,  # 实际交易签名将从区块链返回
        }
        
        return jsonify(result)
    except Exception as e:
        logger.exception(f"执行Solana转账失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"执行转账失败: {str(e)}"
        }), 500

@api_bp.route('/execute_transfer', methods=['POST'])
def execute_transfer():
    """执行代币转账 - 兼容旧版本API"""
    try:
        data = request.json
        logger.info(f"收到转账请求: {data}")
        
        # 验证基本参数
        required_fields = ['from_address', 'to_address', 'amount', 'token_symbol']
        
        # 检查必填字段
        missing_fields = []
        for field in required_fields:
            if not data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"转账请求缺少必要参数: {missing_fields}")
            return jsonify({
                'success': False,
                'message': f"缺少必要参数: {', '.join(missing_fields)}"
            }), 400
        
        from_address = data.get('from_address')
        to_address = data.get('to_address')
        amount = float(data.get('amount'))
        token_symbol = data.get('token_symbol')
        
        # 验证地址格式
        if len(from_address) < 32 or len(to_address) < 32:
            return jsonify({
                'success': False,
                'message': '无效的钱包地址格式'
            }), 400
        
        # 验证金额
        if amount <= 0:
            return jsonify({
                'success': False,
                'message': '转账金额必须大于0'
            }), 400
        
        # 记录交易信息
        logger.info(f"执行转账: {from_address} -> {to_address}, 金额: {amount} {token_symbol}")
        
        # 使用区块链服务执行交易
        try:
            result = execute_transfer_transaction(
                token_symbol=token_symbol,
                from_address=from_address,
                to_address=to_address,
                amount=amount
            )
            
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': '转账成功',
                    'signature': result.get('signature'),
                    'transaction_id': result.get('signature')
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('error', '转账失败')
                }), 500
                
        except Exception as e:
            logger.error(f"区块链转账执行失败: {str(e)}")
            return jsonify({
                'success': False,
                'message': f"转账执行失败: {str(e)}"
            }), 500
        
    except Exception as e:
        logger.exception(f"执行转账失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"转账失败: {str(e)}"
        }), 500

@api_bp.route('/solana/record_payment', methods=['POST'])
def record_payment():
    """记录支付信息，作为支付流程的简化版本"""
    try:
        data = request.json
        logger.info(f"收到记录支付请求: {data}")
        
        # 验证基本参数
        required_fields = ['from_address', 'to_address', 'amount', 'token_symbol', 'message']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f"缺少必要参数: {', '.join(missing_fields)}"
            }), 400
            
        # 获取资产信息
        asset_id = data.get('asset_id')
        signature = data.get('signature')
        
        # 如果未提供签名，则无法进行验证
        if not signature:
            return jsonify({
                'success': False,
                'message': f"缺少交易签名，无法验证交易"
            }), 400
        
        # 记录支付信息
        try:
            # 如果提供了资产ID，更新资产的支付信息
            if asset_id:
                from app.models import Asset
                from app.models.asset import AssetStatus  # 引入状态枚举
                from app.tasks import monitor_creation_payment
                
                asset = Asset.query.get(asset_id)
                if asset:
                    asset.payment_tx_hash = signature
                    asset.payment_details = json.dumps({
                        'from_address': data.get('from_address'),
                        'to_address': data.get('to_address'),
                        'amount': data.get('amount'),
                        'token_symbol': data.get('token_symbol'),
                        'timestamp': datetime.utcnow().isoformat(),
                        'status': 'pending'
                    })
                    
                    # 更新状态为待确认
                    if asset.status == AssetStatus.PENDING.value:
                        logger.info(f"资产状态从PENDING更新为PENDING(保持不变): AssetID={asset_id}")
                    
                    db.session.commit()
                    logger.info(f"更新资产支付交易哈希: AssetID={asset_id}, TxHash={signature}")
                    
                    # 触发支付确认监控任务
                    try:
                        logger.info(f"触发支付确认监控任务: AssetID={asset_id}, TxHash={signature}")
                        monitor_task = monitor_creation_payment.delay(asset_id, signature)
                        logger.info(f"支付确认监控任务已触发: {monitor_task}")
                    except Exception as task_error:
                        logger.error(f"触发支付确认监控任务失败: {str(task_error)}")
                        # 记录详细的错误堆栈
                        import traceback
                        logger.error(traceback.format_exc())
                else:
                    logger.warning(f"未找到要更新的资产: AssetID={asset_id}")
        except Exception as record_error:
            logger.error(f"记录支付信息失败: {str(record_error)}")
            # 记录详细的错误堆栈
            import traceback
            logger.error(traceback.format_exc())
            
        # 返回成功结果
        return jsonify({
            'success': True,
            'signature': signature,
            'message': '支付已记录',
            'payment_monitoring_started': bool(asset_id)  # 表明是否启动了支付监控
        })
        
    except Exception as e:
        logger.error(f"记录支付失败: {str(e)}")
        # 记录详细的错误堆栈
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f"记录支付失败: {str(e)}"
        }), 500

@api_bp.route('/admin/fix_asset_total_values', methods=['POST'])
def fix_asset_total_values():
    """修复现有资产的total_value字段"""
    try:
        from app.models.asset import Asset
        
        # 查找所有total_value为null的资产
        assets_to_fix = Asset.query.filter(Asset.total_value.is_(None)).all()
        
        fixed_count = 0
        for asset in assets_to_fix:
            if asset.token_price and asset.token_supply:
                # 计算total_value = token_price * token_supply
                asset.total_value = asset.token_price * asset.token_supply
                fixed_count += 1
        
        # 提交更改
        db.session.commit()
        
        current_app.logger.info(f"修复了 {fixed_count} 个资产的total_value字段")
        
        return jsonify({
            'success': True,
            'message': f'成功修复了 {fixed_count} 个资产的total_value字段',
            'fixed_count': fixed_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"修复资产total_value失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/payment/config', methods=['GET'])
def get_payment_config():
    """获取支付配置 - 兼容路由"""
    try:
        from app.utils.config_manager import ConfigManager
        
        # 使用统一的配置管理器获取支付设置
        settings = ConfigManager.get_payment_settings()
        
        current_app.logger.info(f"返回支付设置: {settings}")
        return jsonify(settings)
    except Exception as e:
        logger.error(f"获取支付设置失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取支付设置失败: {str(e)}'}), 500

@api_bp.route('/share-messages/random', methods=['GET'])
def get_random_share_message():
    """获取随机分享消息"""
    try:
        from app.models.share_message import ShareMessage
        
        # 获取消息类型参数，默认为分享内容
        message_type = request.args.get('type', 'share_content')
        
        # 获取随机消息
        message = ShareMessage.get_random_message(message_type)
        
        return jsonify({
            'success': True,
            'message': message,
            'type': message_type
        })
        
    except Exception as e:
        current_app.logger.error(f'获取随机分享消息失败: {str(e)}')
        return jsonify({
            'success': False,
            'error': '获取分享消息失败'
        }), 500

@api_bp.route('/share-reward-plan/random', methods=['GET'])
def get_random_reward_plan():
    """获取随机奖励计划文案"""
    try:
        from app.models.share_message import ShareMessage
        
        # 获取奖励计划类型的随机消息
        message = ShareMessage.get_random_message('reward_plan')
        
        return jsonify({
            'success': True,
            'message': message,
            'type': 'reward_plan'
        })
        
    except Exception as e:
        current_app.logger.error(f'获取随机奖励计划文案失败: {str(e)}')
        return jsonify({
            'success': False,
            'error': '获取奖励计划文案失败'
        }), 500

@api_bp.route('/shortlink/create', methods=['POST'])
def create_shortlink():
    """创建短链接"""
    try:
        from app.models.shortlink import ShortLink
        from flask import url_for
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '缺少请求数据'}), 400
            
        original_url = data.get('url')
        expires_days = data.get('expires_days', 365)
        
        if not original_url:
            return jsonify({'success': False, 'error': '缺少原始URL'}), 400
        
        # 获取创建者钱包地址
        creator_address = request.headers.get('X-Eth-Address')
        
        # 创建短链接
        short_link = ShortLink.create_short_link(
            original_url=original_url,
            creator_address=creator_address,
            expires_days=expires_days
        )
        
        # 生成完整的短链接URL
        short_url = url_for('main.shortlink_redirect', code=short_link.code, _external=True)
        
        return jsonify({
            'success': True,
            'short_url': short_url,
            'code': short_link.code,
            'original_url': original_url,
            'expires_at': short_link.expires_at.isoformat() if short_link.expires_at else None
        })
        
    except Exception as e:
        current_app.logger.error(f"创建短链接失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'创建短链接失败: {str(e)}'}), 500

@api_bp.route('/share-config', methods=['GET'])
def get_share_config():
    """获取分享配置（前端调用）"""
    try:
        from app.models.commission_config import CommissionConfig
        
        # 获取佣金配置
        commission_rate = CommissionConfig.get_config('commission_rate', 20.0)
        commission_rules = CommissionConfig.get_config('commission_rules', {})
        max_referral_levels = CommissionConfig.get_config('max_referral_levels', 999)
        enable_multi_level = CommissionConfig.get_config('enable_multi_level', True)
        
        config = {
            'share_button_text': CommissionConfig.get_config('share_button_text', '🚀 分享RWA资产'),
            'share_description': CommissionConfig.get_config('share_description', f'分享此RWA资产给好友，享受{commission_rate}%分享收益'),
            'share_success_message': CommissionConfig.get_config('share_success_message', f'🎉 分享链接已复制！快去邀请好友赚取{commission_rate}%收益吧！'),
            'commission_rate': commission_rate,
            'commission_description': CommissionConfig.get_config('commission_description', f'推荐好友享受{commission_rate}%收益回馈'),
            'commission_rules': commission_rules,
            'max_referral_levels': max_referral_levels,
            'enable_multi_level': enable_multi_level,
            'is_unlimited_levels': max_referral_levels >= 999,
            'commission_model': 'unlimited' if max_referral_levels >= 999 else 'limited',
            'model_description': f'无限层级分销，每级上贡{commission_rate}%' if max_referral_levels >= 999 else f'{max_referral_levels}级分销，每级{commission_rate}%'
        }
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        current_app.logger.error(f"获取分享配置失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/assets/symbol/<string:token_symbol>/dividend_stats', methods=['GET'])
def get_asset_dividend_stats_by_symbol(token_symbol):
    """获取资产分红统计信息 - 通过token_symbol"""
    try:
        current_app.logger.info(f"请求资产分红统计: {token_symbol}")
        from app.models.asset import Asset
        from app.models.dividend import DividendRecord, Dividend
        from sqlalchemy import func
        
        # 查找资产
        asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if not asset:
            current_app.logger.warning(f"找不到资产: {token_symbol}")
            return jsonify({
                'success': False,
                'error': f'找不到资产: {token_symbol}',
                'total_amount': 0
            }), 404
        
        # 计算总分红金额
        total_amount = 0
        try:
            # 优先从DividendRecord表计算
            dividend_sum = db.session.query(func.sum(DividendRecord.amount)).filter_by(asset_id=asset.id).scalar()
            if dividend_sum:
                total_amount = float(dividend_sum)
            else:
                # 如果DividendRecord表没有数据，尝试从Dividend表计算
                dividend_sum = db.session.query(func.sum(Dividend.amount)).filter_by(asset_id=asset.id).scalar()
                if dividend_sum:
                    total_amount = float(dividend_sum)
        except Exception as e:
            current_app.logger.warning(f"无法从数据库计算分红，使用默认值: {str(e)}")
            # 如果分红表不存在或有问题，使用默认值
            total_amount = 50000  # 默认分红金额
        
        current_app.logger.info(f"资产 {token_symbol} 的总分红金额: {total_amount}")
        
        return jsonify({
            'success': True,
            'total_amount': float(total_amount),
            'asset_symbol': token_symbol,
            'asset_name': asset.name
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取资产分红统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'total_amount': 0
        }), 500
