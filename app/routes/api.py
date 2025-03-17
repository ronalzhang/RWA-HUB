from flask import jsonify, request, g, current_app, session, Blueprint, make_response, redirect, url_for, Response
from app.models.user import User
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.trade import Trade, TradeStatus
from app.extensions import db
from app.utils.decorators import token_required, eth_address_required, api_eth_address_required, task_background
from .admin import is_admin
import os
import json
from werkzeug.utils import secure_filename
import random
from app.models.dividend import DividendRecord
from app.utils.storage import storage, upload_file
from app.config import Config as CONFIG
import time
import re
from sqlalchemy.exc import OperationalError
from app.utils.solana import solana_client
from app.models.income import IncomeType, record_income
from datetime import datetime
import hashlib
import logging
import uuid
import requests
from urllib.parse import urlparse
from flask_login import current_user
from sqlalchemy import desc, or_, and_, func, text
# 以下导入模块不存在，需要注释掉
# from ..models.audit_log import AuditLog
# from ..models.history_trade import HistoryTrade
# from ..models.notice import Notice
from app.models.referral import UserReferral, CommissionRecord, DistributionSetting

api_bp = Blueprint('api', __name__)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_admin_address(address):
    """检查地址是否为管理员"""
    if not address:
        return False
    admin_config = current_app.config['ADMIN_CONFIG']
    current_app.logger.info(f'管理员配置: {admin_config}')
    current_app.logger.info(f'检查地址: {address}')
    
    # 将所有地址和待检查地址转换为小写进行比较
    address = address.lower()
    admin_addresses = {addr.lower(): config for addr, config in admin_config.items()}
    
    # 检查地址是否在管理员列表中
    is_admin = address in admin_addresses
    current_app.logger.info(f'检查结果: {is_admin}')
    return is_admin

# 资产API路由
@api_bp.route('/assets/list', methods=['GET'])
def list_assets():
    """获取资产列表"""
    try:
        # 检查是否是管理员
        eth_address = request.headers.get('X-Eth-Address') or \
                     request.args.get('eth_address') or \
                     request.cookies.get('eth_address')
        is_admin = is_admin_address(eth_address)
        
        # 如果是管理员，获取所有资产，否则只获取已审核通过的资产
        query = Asset.query if is_admin else Asset.query.filter_by(status=AssetStatus.APPROVED.value)

        # 过滤掉已删除的资产
        if is_admin:
            query = query.filter(
                Asset.status.in_([
                    AssetStatus.PENDING.value,
                    AssetStatus.APPROVED.value,
                    AssetStatus.REJECTED.value
                ])
            )
        
        # 如果指定了owner参数，则只返回该owner的资产
        owner = request.args.get('owner')
        if owner:
            query = query.filter_by(owner_address=owner)
        
        # 按创建时间倒序排序
        query = query.order_by(Asset.created_at.desc())
        
        # 执行查询
        assets = query.all()
        current_app.logger.info(f'Found {len(assets)} assets')
        
        # 转换为字典格式
        asset_list = []
        for asset in assets:
            try:
                asset_dict = asset.to_dict()
                asset_list.append(asset_dict)
            except Exception as e:
                current_app.logger.error(f'Error converting asset {asset.id} to dict: {str(e)}')
                continue
        
        current_app.logger.info(f'Returning {len(asset_list)} assets')
        return jsonify({
            'assets': asset_list
        })
        
    except Exception as e:
        current_app.logger.error(f'Error listing assets: {str(e)}', exc_info=True)
        return jsonify({'error': '获取资产列表失败'}), 500

@api_bp.route('/assets/<int:asset_id>')
def get_asset(asset_id):
    """获取资产详情 - 使用ID（旧版，保留兼容性）"""
    try:
        current_app.logger.info(f"正在使用ID获取资产详情，ID: {asset_id}")
        asset = Asset.query.get_or_404(asset_id)
        
        # 返回资产详情
        return _get_asset_details(asset)
    except Exception as e:
        current_app.logger.error(f"获取资产详情失败: {str(e)}", exc_info=True)
        return jsonify({"error": f"获取资产详情失败: {str(e)}"}), 500

@api_bp.route('/assets/symbol/<string:token_symbol>')
def get_asset_by_symbol(token_symbol):
    """获取资产详情 - 使用token_symbol（新版）"""
    try:
        current_app.logger.info(f"正在使用token_symbol获取资产详情，token_symbol: {token_symbol}")
        asset = Asset.query.filter_by(token_symbol=token_symbol).first_or_404()
        
        # 返回资产详情
        return _get_asset_details(asset)
    except Exception as e:
        current_app.logger.error(f"获取资产详情失败: {str(e)}", exc_info=True)
        return jsonify({"error": f"获取资产详情失败: {str(e)}"}), 500

@api_bp.route('/assets/<string:token_symbol>', methods=['GET'])
def get_asset_by_symbol_direct(token_symbol):
    """获取资产详情 - 直接使用token_symbol（用于分红页面）"""
    try:
        current_app.logger.info(f"通过直接路径访问资产详情，token_symbol: {token_symbol}")
        asset = Asset.query.filter_by(token_symbol=token_symbol).first_or_404()
        
        # 返回资产详情
        return _get_asset_details(asset)
    except Exception as e:
        current_app.logger.error(f"获取资产详情失败: {str(e)}", exc_info=True)
        return jsonify({"error": f"获取资产详情失败: {str(e)}"}), 500

def _get_asset_details(asset):
    """处理并返回资产详情（抽取的公共方法）"""
    # 处理资产类型，确保返回正确的值
    asset_type_value = asset.asset_type
    if hasattr(asset.asset_type, 'value'):
        asset_type_value = asset.asset_type.value
        
    # 处理状态，确保返回正确的值
    status_value = asset.status
    if hasattr(asset.status, 'value'):
        status_value = asset.status.value

    # 计算已售出代币数量
    tokens_sold = 0
    if asset.token_supply is not None and asset.remaining_supply is not None:
        tokens_sold = asset.token_supply - asset.remaining_supply

    # 获取持有人数 - 基于已完成的购买交易中不同的交易者地址
    unique_holders = db.session.query(Trade.trader_address)\
        .filter(Trade.asset_id == asset.id,
                Trade.type == 'buy',
                Trade.status == 'completed')\
        .distinct().count()
        
    # 构建资产数据
    asset_data = {
        'id': asset.id,
        'name': asset.name,
        'description': asset.description,
        'asset_type': asset_type_value,
        'location': asset.location,
        'area': asset.area,
        'total_value': asset.total_value,
        'token_symbol': asset.token_symbol,
        'token_price': asset.token_price,
        'token_supply': asset.token_supply,
        'token_address': asset.token_address,
        'annual_revenue': asset.annual_revenue,
        'status': status_value,
        'owner_address': asset.owner_address,
        'created_at': asset.created_at.strftime('%Y-%m-%d %H:%M:%S') if asset.created_at else None,
        'updated_at': asset.updated_at.strftime('%Y-%m-%d %H:%M:%S') if asset.updated_at else None,
        'remaining_supply': asset.remaining_supply,
        'tokens_sold': tokens_sold,
        'holder_count': unique_holders
    }
    
    # 处理图片字段
    try:
        if asset.images and isinstance(asset.images, str):
            asset_data['images'] = json.loads(asset.images)
        else:
            asset_data['images'] = asset.images or []
    except:
        asset_data['images'] = []
        
    return jsonify(asset_data)

@api_bp.route('/assets/create', methods=['POST'])
@eth_address_required
def create_asset():
    """创建资产"""
    try:
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'error': '请先连接钱包'}), 401
            
        # 获取请求数据
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
            
        # 验证必填字段
        required_fields = ['name', 'description', 'asset_type', 'location', 'token_symbol', 'token_price', 'token_supply']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'缺少必填字段: {field}'}), 400
                
        # 验证资产类型
        asset_type = AssetType.query.filter_by(name=data.get('asset_type')).first()
        if not asset_type:
            return jsonify({'error': '无效的资产类型'}), 400
            
        # 验证代币符号唯一性
        token_symbol = data.get('token_symbol').upper()
        existing_asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if existing_asset:
            return jsonify({'error': f'代币符号 {token_symbol} 已被使用'}), 400
            
        # 计算总价值
        token_price = float(data.get('token_price') or 0)
        token_supply = int(data.get('token_supply') or 0)
        total_value = token_price * token_supply
            
        def safe_float(value, field_name):
            """安全转换为浮点数"""
            try:
                return float(value) if value else 0
            except (ValueError, TypeError):
                return 0
                
        def safe_int(value, field_name):
            """安全转换为整数"""
            try:
                return int(value) if value else 0
            except (ValueError, TypeError):
                return 0
            
        # 创建资产记录
        asset = Asset(
            name=data.get('name'),
            description=data.get('description'),
            asset_type=asset_type,
            location=data.get('location'),
            total_value=total_value,
            token_symbol=token_symbol,
            token_price=safe_float(data.get('token_price'), '代币价格'),
            token_supply=safe_int(data.get('token_supply'), '代币数量'),
            annual_revenue=safe_float(data.get('annual_revenue'), '年收益'),
            status=AssetStatus.PENDING,
            owner_address=g.eth_address
        )
        
        # 保存到数据库
        db.session.add(asset)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '资产创建成功，等待审核',
            'asset_id': asset.id
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建资产失败: {str(e)}")
        return jsonify({'error': f'创建资产失败: {str(e)}'}), 500

@api_bp.route('/assets/<int:asset_id>', methods=['PUT'])
def update_asset(asset_id):
    eth_address = request.headers.get('X-Eth-Address')
    current_app.logger.info(f"更新资产请求: {{'asset_id': {asset_id}, 'eth_address': {eth_address}}}")
    
    if not eth_address:
        return jsonify({'message': '请先连接钱包'}), 401
        
    if not is_admin(eth_address):
        return jsonify({'message': '只有管理员可以编辑资产'}), 403
        
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({'message': '资产不存在'}), 404
        
    if asset.token_address:
        return jsonify({'message': '已上链资产不可修改'}), 400
        
    try:
        # 更新资产信息
        asset.name = request.form.get('name')
        asset.location = request.form.get('location')
        asset.description = request.form.get('description', asset.description)
        asset.area = float(request.form.get('area')) if request.form.get('area') else None
        asset.total_value = float(request.form.get('totalValue', 0))
        asset.annual_revenue = float(request.form.get('expectedAnnualRevenue', 0))
        asset.token_price = float(request.form.get('tokenPrice', 0))
        asset.token_supply = int(request.form.get('tokenCount', 0))
        asset.token_symbol = request.form.get('tokenSymbol')
        
        # 处理图片和文档
        if 'images[]' in request.files:
            images = request.files.getlist('images[]')
            if images and any(image.filename for image in images):
                asset.images = save_files(images, asset.asset_type.value.lower(), asset_id)
                
        if 'documents[]' in request.files:
            documents = request.files.getlist('documents[]')
            if documents and any(doc.filename for doc in documents):
                asset.documents = save_files(documents, asset.asset_type.value.lower(), asset_id)
                
        db.session.commit()
        return jsonify({'message': '保存成功'})
    except Exception as e:
        current_app.logger.error(f"更新资产失败: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 交易API路由
@api_bp.route('/trades')
@eth_address_required
def list_trades():
    """获取交易历史"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    asset_id = request.args.get('asset_id', type=int)
    raw_trader_address = request.args.get('trader_address', '')
    
    # 区分ETH和SOL地址处理 - ETH地址转小写，SOL保持原样
    trader_address = raw_trader_address.lower() if raw_trader_address.startswith('0x') else raw_trader_address
    
    # 构建查询
    query = Trade.query
    
    # 按资产ID筛选
    if asset_id:
        query = query.filter_by(asset_id=asset_id)
    
    # 按交易者地址筛选
    if trader_address:
        query = query.filter_by(trader_address=trader_address)
    
    try:
        # 分页
        pagination = query.order_by(Trade.created_at.desc()).paginate(
            page=page, per_page=per_page)
        
        trades = [trade.to_dict() for trade in pagination.items]
        
        # 返回数组格式而不是对象格式，以符合前端期望
        return jsonify(trades), 200
    except Exception as e:
        current_app.logger.error(f'获取交易历史失败: {str(e)}')
        # 即使出错也返回空数组，而不是错误信息，以确保前端正常处理
        return jsonify([]), 200

@api_bp.route('/trades', methods=['POST'])
@eth_address_required
def create_trade():
    """创建交易记录"""
    try:
        data = request.json
        
        # 检查必须的字段
        required_fields = ['asset_id', 'amount', 'type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'缺少必须的字段: {field}'}), 400
        
        # 获取资产
        asset_id = data.get('asset_id')
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({'error': '资产不存在'}), 404
            
        # 验证交易类型
        trade_type = data.get('type')
        if trade_type not in ['buy', 'sell']:
            return jsonify({'error': '无效的交易类型'}), 400
            
        # 验证交易数量
        amount = int(data.get('amount'))
        if amount <= 0:
            return jsonify({'error': '交易数量必须大于0'}), 400
        
        # 计算交易金额和佣金
        price = float(asset.token_price)
        total = price * amount
        
        # 检查是否是自交易
        owner_address = asset.owner_address
        user_address = g.eth_address
        
        # 区分ETH和SOL地址的比较
        if owner_address.startswith('0x') and user_address.startswith('0x'):
            # ETH地址比较时都转为小写
            is_self_trade = owner_address.lower() == user_address.lower()
        else:
            # SOL地址或其他类型地址直接比较（大小写敏感）
            is_self_trade = owner_address == user_address
        
        # 根据交易金额和是否自持确定佣金费率
        if is_self_trade:
            fee_rate = 0.001  # 自持交易优惠费率 0.1%
        elif total >= 100000:  # 大额交易阈值修改为100,000 USDC
            fee_rate = 0.025  # 大额交易优惠费率 2.5%
        else:
            fee_rate = 0.035  # 标准费率 3.5%
            
        # 计算佣金金额
        fee = total * fee_rate
        
        # 使用用户地址的原始大小写，让模型的validator处理
        trader_address = user_address
            
        # 创建交易记录
        trade = Trade(
            asset_id=asset_id,
            trader_address=trader_address,
            amount=amount,
            price=price,
            total=total,
            fee=fee,
            fee_rate=fee_rate,
            type=trade_type,
            status='pending',
            is_self_trade=is_self_trade
        )
        
        db.session.add(trade)
        db.session.commit()
        
        # 交易创建后，计算并创建分销佣金记录
        create_distribution_commissions(trade)
        
        return jsonify(trade.to_dict())
        
    except Exception as e:
        current_app.logger.error(f'创建交易记录失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/trades/<int:trade_id>/update', methods=['POST'])
def update_trade_status(trade_id):
    """更新交易状态"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'error': '无效的请求数据'}), 400
            
        new_status = data['status']
        tx_hash = data.get('tx_hash', '')
        
        # 获取交易记录
        trade = Trade.query.get_or_404(trade_id)
        
        # 更新交易状态
        old_status = trade.status
        trade.status = new_status
        
        # 如果提供了交易哈希，也更新交易哈希
        if tx_hash:
            trade.tx_hash = tx_hash
            
        # 记录交易确认时间
        if new_status == TradeStatus.COMPLETED.value and old_status != TradeStatus.COMPLETED.value:
            trade.confirmed_at = datetime.utcnow()
            
            # 如果是已完成的买入交易，更新资产剩余供应量
            if trade.type == 'buy':
                asset = Asset.query.get(trade.asset_id)
                if asset and asset.remaining_supply is not None:
                    asset.remaining_supply -= trade.amount
                    db.session.add(asset)
            
            # 如果是卖出交易，更新资产剩余供应量（增加）
            elif trade.type == 'sell':
                asset = Asset.query.get(trade.asset_id)
                if asset and asset.remaining_supply is not None:
                    asset.remaining_supply += trade.amount
                    db.session.add(asset)
            
            # 如果是买入交易，同步处理分销佣金记录
            if trade.type == 'buy':
                try:
                    create_distribution_commissions(trade)
                except Exception as e:
                    current_app.logger.error(f'处理分销佣金失败: {str(e)}')
                    # 佣金处理失败不应该影响主交易流程
        
        db.session.add(trade)
        db.session.commit()
        
        return jsonify({
            'id': trade.id,
            'status': trade.status,
            'tx_hash': trade.tx_hash
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'更新交易状态失败: {str(e)}')
        return jsonify({'error': '更新交易状态失败'}), 500

def create_distribution_commissions(trade):
    """计算并创建分销佣金记录"""
    try:
        # 只处理购买类型的交易
        if trade.type != 'buy':
            return
        
        # 获取买家地址
        buyer_address = trade.trader_address
        
        # 查找买家的推荐关系链
        referrals = []
        
        # 查找一级推荐人
        level1_referral = UserReferral.query.filter_by(user_address=buyer_address).first()
        if level1_referral:
            referrals.append({
                'address': level1_referral.referrer_address,
                'level': 1
            })
            
            # 查找二级推荐人
            level2_referral = UserReferral.query.filter_by(
                user_address=level1_referral.referrer_address
            ).first()
            if level2_referral:
                referrals.append({
                    'address': level2_referral.referrer_address,
                    'level': 2
                })
                
                # 查找三级推荐人
                level3_referral = UserReferral.query.filter_by(
                    user_address=level2_referral.referrer_address
                ).first()
                if level3_referral:
                    referrals.append({
                        'address': level3_referral.referrer_address,
                        'level': 3
                    })
        
        # 如果没有推荐关系，只创建平台佣金记录
        if not referrals:
            # 获取平台地址
            platform_address = current_app.config.get('PLATFORM_ADDRESS', '0x0000000000000000000000000000000000000000')
            
            # 创建平台佣金记录
            platform_commission = CommissionRecord(
                transaction_id=trade.id,
                asset_id=trade.asset_id,
                recipient_address=platform_address,
                amount=trade.fee,
                commission_type='platform',
                status='pending'
            )
            db.session.add(platform_commission)
            db.session.commit()
            return
        
        # 获取分销比例设置
        distribution_settings = {
            1: 0.3,  # 一级分销比例：30%
            2: 0.15,  # 二级分销比例：15%
            3: 0.05   # 三级分销比例：5%
        }
        
        # 从数据库获取最新设置
        settings = DistributionSetting.query.filter_by(is_active=True).all()
        for setting in settings:
            distribution_settings[setting.level] = setting.commission_rate
        
        # 总分销佣金比例
        total_distribution_rate = sum(distribution_settings.values())
        
        # 计算分销佣金和平台佣金
        total_fee = trade.fee
        platform_fee = total_fee * (1 - total_distribution_rate)
        
        # 创建佣金记录
        commission_records = []
        
        # 平台佣金记录
        platform_address = current_app.config.get('PLATFORM_ADDRESS', '0x0000000000000000000000000000000000000000')
        platform_commission = CommissionRecord(
            transaction_id=trade.id,
            asset_id=trade.asset_id,
            recipient_address=platform_address,
            amount=platform_fee,
            commission_type='platform',
            status='pending'
        )
        commission_records.append(platform_commission)
        
        # 分销佣金记录
        for referral in referrals:
            level = referral['level']
            rate = distribution_settings.get(level, 0)
            if rate > 0:
                commission_amount = total_fee * rate
                commission = CommissionRecord(
                    transaction_id=trade.id,
                    asset_id=trade.asset_id,
                    recipient_address=referral['address'],
                    amount=commission_amount,
                    commission_type=f'referral_{level}',
                    referral_level=level,
                    status='pending'
                )
                commission_records.append(commission)
        
        # 保存所有佣金记录
        for record in commission_records:
            db.session.add(record)
        db.session.commit()
        
        current_app.logger.info(f'为交易 #{trade.id} 创建了 {len(commission_records)} 条佣金记录')
    except Exception as e:
        current_app.logger.error(f'创建分销佣金记录失败: {str(e)}')
        # 失败时不应该影响主交易流程，所以只记录日志
        db.session.rollback()

@api_bp.route("/<int:asset_id>/check_owner", methods=['GET'])
def check_asset_owner(asset_id):
    """检查当前地址是否为资产发布者或管理员"""
    eth_address = request.headers.get('X-Eth-Address')
    if not eth_address:
        return jsonify({'error': '未提供钱包地址'}), 400

    try:
        # 检查资产是否存在
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({'error': '资产不存在'}), 404

        # 检查是否为资产发布者
        is_owner = eth_address.lower() == asset.publisher_address.lower()
        
        # 检查是否为管理员
        is_admin = eth_address.lower() in [addr.lower() for addr in current_app.config['ADMIN_ADDRESSES']]

        return jsonify({
            'is_owner': is_owner,
            'is_admin': is_admin
        })
    except Exception as e:
        current_app.logger.error(f'检查资产所有者失败: {str(e)}')
        return jsonify({'error': '检查资产所有者失败'}), 500

@api_bp.route("/assets/symbol/<string:token_symbol>/transactions", methods=['GET'])
def get_asset_transactions_by_symbol(token_symbol):
    """获取资产交易记录 - 使用token_symbol"""
    try:
        # 检查资产是否存在
        asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if not asset:
            return jsonify({'error': '资产不存在'}), 404

        # 获取交易记录
        transactions = Trade.query.filter_by(asset_id=asset.id).order_by(Trade.created_at.desc()).all()
        
        # 转换为JSON
        data = []
        for tx in transactions:
            data.append({
                'id': tx.id,
                'type': tx.type,
                'amount': tx.amount,
                'price': tx.price,
                'total': tx.total,
                'trader_address': tx.trader_address,
                'status': tx.status,
                'tx_hash': tx.tx_hash,
                'created_at': tx.created_at.strftime('%Y-%m-%d %H:%M:%S') if tx.created_at else None
            })
            
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f'获取交易记录失败: {str(e)}')
        return jsonify({'error': '获取交易记录失败'}), 500

@api_bp.route("/assets/symbol/<string:token_symbol>/dividend_stats", methods=['GET'])
def get_dividend_stats_by_symbol(token_symbol):
    """获取资产分红统计信息 - 使用token_symbol"""
    try:
        # 检查资产是否存在
        asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if not asset:
            return jsonify({'error': '资产不存在'}), 404

        # 从数据库获取实际的分红统计数据
        # 1. 获取分红次数和总金额
        dividend_records = DividendRecord.query.filter_by(asset_id=asset.id).all()
        dividend_count = len(dividend_records)
        total_dividend = sum(record.amount for record in dividend_records) if dividend_records else 0
        
        # 2. 获取持有人数 - 基于已完成的购买交易中不同的交易者地址
        unique_holders = db.session.query(Trade.trader_address)\
            .filter(Trade.asset_id == asset.id,
                    Trade.type == 'buy',  # 使用字符串 'buy' 替代 TradeType.BUY.value
                    Trade.status == 'completed')\
            .distinct().count()
        
        # 3. 计算已售出代币数量
        tokens_sold = 0
        if asset.token_supply is not None and asset.remaining_supply is not None:
            tokens_sold = asset.token_supply - asset.remaining_supply
        
        data = {
            'count': dividend_count,  # 分红次数
            'total_amount': total_dividend,  # 累计分红金额
            'holder_count': unique_holders,  # 当前持有人数
            'tokens_sold': tokens_sold  # 已售出代币数量
        }

        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f'获取分红统计失败: {str(e)}')
        return jsonify({'error': '获取分红统计失败'}), 500

@api_bp.route("/assets/symbol/<string:token_symbol>/dividend_history", methods=['GET'])
def get_dividend_history_by_symbol(token_symbol):
    """获取资产分红历史记录 - 使用token_symbol"""
    try:
        # 检查资产是否存在
        asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if not asset:
            return jsonify({'error': '资产不存在'}), 404

        # 获取分红记录
        records = DividendRecord.query.filter_by(asset_id=asset.id).order_by(DividendRecord.created_at.desc()).all()
        
        # 转换为JSON
        data = []
        for record in records:
            # 使用 to_dict 方法如果存在，否则手动构建字典
            if hasattr(record, 'to_dict'):
                record_data = record.to_dict()
            else:
                record_data = {
                    'id': record.id,
                    'asset_id': record.asset_id,
                    'amount': record.amount,
                    'date': record.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # 添加transaction_hash字段(如果存在)
                if hasattr(record, 'transaction_hash'):
                    record_data['transaction_hash'] = record.transaction_hash
            
            data.append(record_data)
            
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f'获取分红历史失败: {str(e)}')
        # 在出错的情况下返回空列表而不是错误，以免前端显示崩溃
        return jsonify([])

@api_bp.route('/check_admin', methods=['POST'])
def check_admin():
    try:
        data = request.get_json()
        if not data or 'address' not in data:
            return jsonify({'error': 'Missing address parameter'}), 400
            
        address = data['address'].lower()  # 转换为小写
        # 使用 is_admin_address 函数检查是否是管理员
        is_admin = is_admin_address(address)
        
        if is_admin:
            # 获取管理员配置信息
            admin_config = current_app.config['ADMIN_CONFIG']
            # 尝试用小写和原始地址获取配置
            admin_info = admin_config.get(address) or next(
                (config for key, config in admin_config.items() if key.lower() == address),
                None
            )
            
            if admin_info:
                return jsonify({
                    'is_admin': True,
                    'role': admin_info['role'],
                    'name': admin_info.get('name', ''),
                    'level': admin_info.get('level', 1),
                    'permissions': admin_info['permissions']
                })
        
        return jsonify({
            'is_admin': False,
            'admin_config': None
        })
    except Exception as e:
        current_app.logger.error(f'检查管理员状态失败: {str(e)}')
        return jsonify({'error': '检查管理员状态失败'}), 500 

@api_bp.route('/assets/<int:asset_id>/check_permission', methods=['GET'])
@eth_address_required
def check_asset_permission(asset_id):
    """检查资产权限 - 使用ID（旧版，保留兼容性）"""
    try:
        # 获取资产信息
        asset = Asset.query.get_or_404(asset_id)
        
        # 检查是否是所有者
        is_owner = g.eth_address.lower() == asset.owner_address.lower()
        
        # 检查是否是管理员
        is_admin_user = is_admin(g.eth_address)
        
        # 检查是否可以管理分红
        can_manage_dividend = is_owner or is_admin_user
        
        return jsonify({
            'is_owner': is_owner,
            'is_admin': is_admin_user,
            'can_manage_dividend': can_manage_dividend
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'检查资产权限失败: {str(e)}')
        return jsonify({
            'error': '检查资产权限失败',
            'is_owner': False,
            'is_admin': False,
            'can_manage_dividend': False
        }), 500

@api_bp.route('/assets/symbol/<string:token_symbol>/check_permission', methods=['GET'])
@eth_address_required
def check_asset_permission_by_symbol(token_symbol):
    """检查资产权限 - 使用token_symbol（新版）"""
    try:
        current_app.logger.info(f"使用token_symbol检查资产权限，token_symbol: {token_symbol}")
        # 获取资产信息
        asset = Asset.query.filter_by(token_symbol=token_symbol).first_or_404()
        
        # 检查是否是所有者
        is_owner = g.eth_address.lower() == asset.owner_address.lower()
        
        # 检查是否是管理员
        is_admin_user = is_admin(g.eth_address)
        
        # 检查是否可以管理分红
        can_manage_dividend = is_owner or is_admin_user
        
        return jsonify({
            'is_owner': is_owner,
            'is_admin': is_admin_user,
            'can_manage_dividend': can_manage_dividend
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'使用token_symbol检查资产权限失败: {str(e)}')
        return jsonify({
            'error': '检查资产权限失败',
            'is_owner': False,
            'is_admin': False,
            'can_manage_dividend': False
        }), 500

@api_bp.route('/assets/<int:asset_id>/holders', methods=['GET'])
def get_asset_holders(asset_id):
    """获取资产持有人信息"""
    try:
        # 检查资产是否存在
        asset = Asset.query.get_or_404(asset_id)
        
        # 检查请求者是否是资产所有者
        eth_address = request.headers.get('X-Eth-Address')
        if not eth_address or eth_address.lower() != asset.owner_address.lower():
            return jsonify({'error': '无权访问'}), 403
            
        # 模拟返回持有人数据
        return jsonify({
            'holders_count': 100,  # 模拟数据
            'total_supply': asset.token_count
        })
        
    except Exception as e:
        current_app.logger.error(f'获取资产持有人信息失败: {str(e)}')
        return jsonify({'error': '获取持有人信息失败'}), 500

@api_bp.route('/user/assets')
@eth_address_required
def get_user_assets():
    """获取用户持有的资产数据"""
    try:
        # 获取用户地址
        user_address = g.eth_address
        
        # 根据地址类型处理
        if user_address.startswith('0x'):
            # ETH地址，查询原始大小写地址和小写地址
            completed_trades = Trade.query.filter(
                Trade.trader_address.in_([user_address, user_address.lower()]),
                Trade.status == TradeStatus.COMPLETED.value
            ).all()
        else:
            # SOL地址或其他类型，查询原始地址（区分大小写）
            completed_trades = Trade.query.filter_by(
                trader_address=user_address,
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
                
            asset = Asset.query.get(asset_id)
            if not asset:
                continue
            
            # 处理图片URL
            image_url = None
            if asset.images:
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
        
        # 按持有价值降序排序
        user_assets.sort(key=lambda x: x['total_value'], reverse=True)
        
        return jsonify(user_assets), 200
    except Exception as e:
        current_app.logger.error(f'获取用户资产失败: {str(e)}', exc_info=True)
        return jsonify([]), 200  # 即使发生错误也返回空数组而不是错误信息
