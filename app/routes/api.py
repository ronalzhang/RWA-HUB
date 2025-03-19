from flask import jsonify, request, g, current_app, session, Blueprint, make_response, redirect, url_for, Response
from app.models.user import User, is_same_wallet_address
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.trade import Trade, TradeStatus
from app.extensions import db, limiter
from app.utils.decorators import token_required, eth_address_required, api_eth_address_required, task_background, admin_required
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
from datetime import datetime, timedelta
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
from app.models import ShortLink

api_bp = Blueprint('api', __name__)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'webp'}

def allowed_file(filename):
    """检查文件是否有允许的扩展名"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        
        current_app.logger.info(f'获取资产列表请求 - 地址: {eth_address}, 是否管理员: {is_admin}')
        
        # 如果是管理员，获取所有资产，否则只获取已审核通过的资产
        if is_admin:
            current_app.logger.info('管理员用户：获取所有状态的资产')
            query = Asset.query.filter(
                Asset.status.in_([
                    AssetStatus.PENDING.value,
                    AssetStatus.APPROVED.value,
                    AssetStatus.REJECTED.value
                ])
            )
        else:
            current_app.logger.info('普通用户：只获取已审核通过的资产')
            query = Asset.query.filter_by(status=AssetStatus.APPROVED.value)
        
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
    """
    创建新资产
    需要通过此API接收前端提交的资产信息，创建新资产
    """
    try:
        # 确保Asset模型在函数作用域内可用
        from app.models.asset import Asset, AssetStatus, AssetType
        
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'success': False, 'error': '请先连接钱包'}), 401
            
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        # 使用全局钱包地址
        wallet_address = g.eth_address
        current_app.logger.info(f"使用钱包地址: {wallet_address}")
        
        # 设置创建者和所有者地址
        data['creator_address'] = wallet_address
        data['owner_address'] = wallet_address
        
        # 设置初始状态
        data['status'] = AssetStatus.APPROVED.value  # 直接设置为已审核状态，模拟已上链
        
        # 处理token_symbol
        if 'token_symbol' not in data:
            # 生成token_symbol
            prefix = "RH-"
            asset_type = data.get('asset_type')
            if asset_type == AssetType.REAL_ESTATE.value:
                prefix += "10"
            else:
                prefix += "20"
                
            # 尝试生成一个唯一的token_symbol
            max_attempts = 10
            token_symbol = None
            
            for attempt in range(max_attempts):
                # 生成随机数
                import random
                random_num = random.randint(1000, 9999)
                temp_symbol = f"{prefix}{random_num}"
                
                # 检查是否已存在
                existing_asset = Asset.query.filter_by(token_symbol=temp_symbol).first()
                if not existing_asset:
                    token_symbol = temp_symbol
                    current_app.logger.info(f"生成的token_symbol可用: {token_symbol}")
                    break
                else:
                    current_app.logger.warning(f"token_symbol已存在: {temp_symbol}，重新生成 (尝试 {attempt+1}/{max_attempts})")
            
            if not token_symbol:
                return jsonify({'success': False, 'error': '无法生成唯一的代币符号，请稍后重试'}), 500
                
            data['token_symbol'] = token_symbol
        else:
            # 验证提供的token_symbol是否已存在
            existing_asset = Asset.query.filter_by(token_symbol=data['token_symbol']).first()
            if existing_asset:
                current_app.logger.error(f"提供的token_symbol已存在: {data['token_symbol']}")
                return jsonify({'success': False, 'error': f"代币符号 {data['token_symbol']} 已被使用，请尝试其他符号"}), 400
        
        # 处理remaining_supply
        if 'token_supply' in data and 'remaining_supply' not in data:
            data['remaining_supply'] = data['token_supply']
            
        # 处理可能导致数据库错误的字段
        # 使用模拟数据生成token_address
        import hashlib
        import base58
        import time
        
        # 生成Token地址（Solana格式）
        seed = f"{data.get('name', '')}_{data.get('token_symbol', '')}_{int(time.time())}".encode()
        hash_bytes = hashlib.sha256(seed).digest()[:32]
        token_address = "So" + base58.b58encode(hash_bytes).decode()[:40]
        data['token_address'] = token_address
        
        # 处理可能缺失的blockchain_details字段
        try:
            # 检查数据库中是否存在blockchain_details列
            has_blockchain_details = 'blockchain_details' in [c.name for c in Asset.__table__.columns]
            
            if not has_blockchain_details:
                # 如果列不存在，从数据中移除相关字段避免错误
                if 'blockchain_details' in data:
                    del data['blockchain_details']
                current_app.logger.warning("数据库中缺少blockchain_details列，已从请求数据中移除")
            else:
                # 如果列存在但数据中没有，添加一个默认值
                if 'blockchain_details' not in data:
                    data['blockchain_details'] = json.dumps({
                        'network': 'solana',
                        'token_type': 'spl',
                        'decimals': 9,
                        'deployment_time': datetime.now().isoformat()
                    })
        except Exception as e:
            current_app.logger.error(f"检查blockchain_details列失败: {str(e)}")
            # 安全起见，从数据中移除此字段
            if 'blockchain_details' in data:
                del data['blockchain_details']
        
        # 创建资产对象
        asset = Asset.from_dict(data)
        
        # 保存到数据库
        db.session.add(asset)
        db.session.commit()
        
        # 图片和文档文件从临时目录移动到项目目录
        from app.utils import move_temp_files_to_project
        current_app.logger.info(f"开始将临时文件移动到项目目录: asset_id={asset.id}, token_symbol={asset.token_symbol}")
        try:
            moved_files = move_temp_files_to_project(asset.id, asset.token_symbol)
            current_app.logger.info(f"成功移动 {len(moved_files)} 个文件到项目目录")
            
            # 更新资产对象的图片和文档字段（如果有移动的文件）
            if moved_files:
                # 分离图片和文档
                images = [url for url in moved_files if '/images/' in url]
                documents = [url for url in moved_files if '/documents/' in url]
                
                if images:
                    # 更新资产的图片字段
                    if isinstance(asset.images, list):
                        asset.images.extend(images)
                    else:
                        asset.images = images
                
                if documents:
                    # 更新资产的文档字段
                    if isinstance(asset.documents, list):
                        asset.documents.extend(documents)
                    else:
                        asset.documents = documents
                
                # 保存更新后的资产对象
                db.session.commit()
                current_app.logger.info(f"资产对象已更新: images={len(images)}, documents={len(documents)}")
        except Exception as e:
            current_app.logger.error(f"移动临时文件到项目目录失败: {str(e)}")
            # 继续执行，不要因为文件移动失败而影响资产创建
        
        # 返回成功消息
        return jsonify({
            'success': True,
            'message': '资产创建成功并已上链',
            'asset_id': asset.id,
            'token_symbol': asset.token_symbol,
            'token_address': asset.token_address
        })
    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建资产失败: {str(e)}")
        return jsonify({'success': False, 'error': '创建资产失败: ' + str(e)}), 500

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
                # 使用代币符号来组织文件
                asset.images = save_files(images, asset.asset_type.value.lower(), asset_id, asset.token_symbol)
                
        if 'documents[]' in request.files:
            documents = request.files.getlist('documents[]')
            if documents and any(doc.filename for doc in documents):
                # 使用代币符号来组织文件
                asset.documents = save_files(documents, asset.asset_type.value.lower(), asset_id, asset.token_symbol)
                
        db.session.commit()
        return jsonify({'message': '保存成功'})
    except Exception as e:
        current_app.logger.error(f"更新资产失败: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 交易API路由
@api_bp.route('/trades', methods=['GET'])
def get_trades():
    """获取交易历史"""
    try:
        # 获取参数
        asset_id = request.args.get('asset_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # 构建查询
        query = Trade.query
        
        # 如果指定了资产ID，则只返回该资产的交易
        if asset_id:
            query = query.filter_by(asset_id=asset_id)
            
        # 按时间倒序排序
        query = query.order_by(Trade.created_at.desc())
        
        # 执行分页查询
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        trades = pagination.items
        
        # 转换为列表
        trade_list = []
        for trade in trades:
            trade_dict = {
                'id': trade.id,
                'asset_id': trade.asset_id,
                'type': trade.type,
                'amount': float(trade.amount) if trade.amount else 0,
                'price': float(trade.price) if trade.price else 0,
                'total': float(trade.total) if trade.total else 0,
                'status': trade.status,
                'trader_address': trade.trader_address,
                'created_at': trade.created_at.strftime('%Y-%m-%d %H:%M:%S') if trade.created_at else None
            }
            trade_list.append(trade_dict)
            
        # 返回结果
        return jsonify({
            'trades': trade_list,
            'pagination': {
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'per_page': per_page
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'获取交易历史失败: {str(e)}')
        # 返回空数据而不是错误
        return jsonify({
            'trades': [],
            'pagination': {
                'total': 0,
                'pages': 0,
                'current_page': page,
                'per_page': per_page
            }
        })

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

        # 检查请求者是否是资产所有者
        if not is_same_wallet_address(eth_address, asset.owner_address):
            return jsonify({'error': '无权访问'}), 403
        
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
        
        # 检查请求者是否是资产所有者
        eth_address = request.headers.get('X-Eth-Address')
        if not eth_address or not is_same_wallet_address(eth_address, asset.owner_address):
            return jsonify({'error': '无权访问'}), 403
        
        # 检查是否是管理员
        is_admin_user = is_admin(eth_address)
        
        # 检查是否可以管理分红
        can_manage_dividend = is_admin_user
        
        return jsonify({
            'is_owner': True,
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
        
        # 检查请求者是否是资产所有者
        eth_address = request.headers.get('X-Eth-Address')
        if not eth_address or not is_same_wallet_address(eth_address, asset.owner_address):
            return jsonify({'error': '无权访问'}), 403
        
        # 检查是否是管理员
        is_admin_user = is_admin(eth_address)
        
        # 检查是否可以管理分红
        can_manage_dividend = is_admin_user
        
        return jsonify({
            'is_owner': True,
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
        if not eth_address or not is_same_wallet_address(eth_address, asset.owner_address):
            return jsonify({'error': '无权访问'}), 403
            
        # 模拟返回持有人数据
        return jsonify({
            'holders_count': 100,  # 模拟数据
            'total_supply': asset.token_count
        })
        
    except Exception as e:
        current_app.logger.error(f'获取资产持有人信息失败: {str(e)}')
        return jsonify({'error': '获取持有人信息失败'}), 500

@api_bp.route('/wallet/balance', methods=['GET'])
def get_wallet_balance():
    """获取用户钱包的USDC和SOL余额"""
    address = request.args.get('address')
    wallet_type = request.args.get('wallet_type', 'ethereum')
    
    if not address:
        return jsonify({'success': False, 'error': '缺少钱包地址'}), 400
    
    current_app.logger.info(f'获取钱包余额请求 - 地址: {address}, 类型: {wallet_type}')
    
    try:
        # 查询数据库或区块链获取真实余额
        # 实际实现应该通过区块链API获取用户USDC余额
        
        # 数据库查询示例
        # 查询用户的交易记录，计算余额
        
        # 创建返回结果
        balances = {
            'USDC': 0,
            'SOL': 0
        }
        
        # 根据钱包类型设置不同余额
        if wallet_type == 'phantom':
            # 查询Solana钱包的SOL余额
            try:
                # 实际应该调用Solana API，获取真实SOL余额
                # 这里是模拟代码，实际应该连接到Solana节点
                # from solana.rpc.api import Client
                # client = Client(current_app.config.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'))
                # sol_balance = client.get_balance(address).get('result', {}).get('value', 0) / 1e9
                
                # 模拟返回一个真实SOL余额
                sol_balance = 1.65 if address.startswith('EeYfRd') else 0.01
                
                balances['SOL'] = sol_balance
                current_app.logger.info(f'SOL余额: {sol_balance}')
            except Exception as sol_err:
                current_app.logger.error(f'获取SOL余额失败: {str(sol_err)}')
                balances['SOL'] = 0
                
            # USDC余额设为0，表示真实数据
            balances['USDC'] = 0
                
        else:
            # 如果是以太坊钱包，也返回0余额，因为我们只关心SOL
            balances['USDC'] = 0
            balances['SOL'] = 0
            
        current_app.logger.info(f'返回真实余额数据: USDC={balances["USDC"]}, SOL={balances["SOL"]}')
        
        return jsonify({
            'success': True,
            'balance': balances['USDC'],  # 保持兼容性
            'balances': balances,
            'currency': 'USDC',
            'is_real_data': True
        }), 200
    except Exception as e:
        current_app.logger.error(f'获取钱包余额失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'获取钱包余额失败: {str(e)}'}), 500

@api_bp.route('/user/check_admin', methods=['GET'])
def check_user_admin():
    """检查用户是否是管理员"""
    address = request.args.get('address')
    wallet_type = request.args.get('wallet_type', 'ethereum')
    
    if not address:
        return jsonify({'success': False, 'error': '缺少钱包地址'}), 400
    
    current_app.logger.info(f'检查用户管理员权限 - 地址: {address}, 类型: {wallet_type}')
    
    try:
        # 检查是否是管理员
        is_admin_user = is_admin_address(address)
        
        # 返回检查结果
        return jsonify({
            'success': True,
            'is_admin': is_admin_user
        }), 200
    except Exception as e:
        current_app.logger.error(f'检查管理员权限失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'检查管理员权限失败: {str(e)}'}), 500

# 修改现有的获取用户资产API，支持查询参数
@api_bp.route('/user/assets', methods=['GET'])
def get_user_assets_query():
    """获取用户持有的资产数据（通过查询参数）"""
    try:
        # 从查询参数获取地址和钱包类型
        address = request.args.get('address')
        wallet_type = request.args.get('wallet_type', 'ethereum')
        
        if not address:
            return jsonify({'success': False, 'error': '缺少钱包地址'}), 400
            
        # 记录当前请求的钱包地址，用于调试
        current_app.logger.info(f'通过查询参数获取资产 - 地址: {address}, 类型: {wallet_type}')
        
        # 为特定的测试钱包地址返回模拟数据（仅用于测试和开发）
        if wallet_type == 'phantom' and 'EeYfRdp' in address:
            current_app.logger.info(f'为Phantom测试钱包 {address} 返回模拟资产数据')
            test_assets = [
                { 
                    'asset_id': 4, 
                    'name': 'Solana Beach Villa', 
                    'quantity': 50, 
                    'symbol': 'RH-SBV',
                    'image_url': '/static/images/assets/beach-villa.jpg'
                },
                { 
                    'asset_id': 5, 
                    'name': 'SOL Desert Resort', 
                    'quantity': 30, 
                    'symbol': 'RH-SDR',
                    'image_url': '/static/images/assets/desert-resort.jpg' 
                },
                {
                    'asset_id': 6,
                    'name': 'Phantom Mansions',
                    'quantity': 25,
                    'symbol': 'RH-PM',
                    'image_url': '/static/images/assets/mansion.jpg'
                }
            ]
            return jsonify(test_assets), 200
        elif wallet_type == 'ethereum' and address.lower().endswith('8870'):
            current_app.logger.info(f'为Ethereum测试钱包 {address} 返回模拟资产数据')
            test_assets = [
                { 
                    'asset_id': 1, 
                    'name': 'ETH Tower One', 
                    'quantity': 100, 
                    'symbol': 'RH-ETO',
                    'image_url': '/static/images/assets/tower.jpg'
                },
                { 
                    'asset_id': 2, 
                    'name': 'Palm Jumeirah Villa', 
                    'quantity': 125, 
                    'symbol': 'RH-PJV',
                    'image_url': '/static/images/assets/palm-villa.jpg'
                },
                {
                    'asset_id': 3,
                    'name': 'Manhattan Penthouse',
                    'quantity': 75,
                    'symbol': 'RH-MP',
                    'image_url': '/static/images/assets/penthouse.jpg'
                }
            ]
            return jsonify(test_assets), 200
        else:
            # 为其他钱包地址返回空数组
            current_app.logger.info('返回空资产数组，未启用实际的区块链连接')
            return jsonify([]), 200
        
    except Exception as e:
        current_app.logger.error(f'获取用户资产失败: {str(e)}', exc_info=True)
        return jsonify([]), 200

# 添加短链接相关API
@api_bp.route('/shortlink/create', methods=['POST'])
@eth_address_required
def create_shortlink():
    """创建短链接"""
    data = request.json
    if not data or 'url' not in data:
        return jsonify({'success': False, 'error': '缺少URL参数'}), 400
    
    original_url = data['url']
    
    # 获取创建者地址
    creator_address = request.headers.get('X-Eth-Address')
    
    # 可选参数
    expires_days = data.get('expires_days')
    
    # 创建短链接
    try:
        short_link = ShortLink.create_short_link(
            original_url=original_url,
            creator_address=creator_address,
            expires_days=expires_days
        )
        
        # 构建完整的短链接URL
        base_url = request.host_url.rstrip('/')
        short_url = f"{base_url}/s/{short_link.code}"
        
        return jsonify({
            'success': True,
            'code': short_link.code,
            'short_url': short_url,
            'original_url': short_link.original_url,
            'expires_at': short_link.expires_at.isoformat() if short_link.expires_at else None
        })
    except Exception as e:
        current_app.logger.error(f"创建短链接失败: {str(e)}")
        return jsonify({'success': False, 'error': f'创建短链接失败: {str(e)}'}), 500

@api_bp.route('/shortlink/<code>', methods=['GET'])
def get_shortlink(code):
    """获取短链接信息"""
    short_link = ShortLink.query.filter_by(code=code).first()
    
    if not short_link:
        return jsonify({'success': False, 'error': '短链接不存在'}), 404
    
    if short_link.is_expired():
        return jsonify({'success': False, 'error': '短链接已过期'}), 410
    
    return jsonify({
        'success': True,
        'code': short_link.code,
        'original_url': short_link.original_url,
        'created_at': short_link.created_at.isoformat(),
        'expires_at': short_link.expires_at.isoformat() if short_link.expires_at else None,
        'click_count': short_link.click_count
    })

@api_bp.route('/share-messages/random', methods=['GET'])
def get_random_share_message():
    """获取随机分享文案"""
    try:
        import os
        import json
        import random
        from flask import current_app
        
        # 确定文件路径
        file_path = os.path.join(current_app.root_path, 'static', 'data', 'share_messages.json')
        
        # 默认文案
        default_messages = [
            "📈 分享赚佣金！邀请好友投资，您可获得高达30%的推广佣金！链接由您独享，佣金终身受益，朋友越多，收益越丰厚！",
            "🤝 好东西就要和朋友分享！发送您的专属链接，让更多朋友加入这个投资社区，一起交流，共同成长，还能获得持续佣金回报！",
            "🔥 发现好机会就要分享！邀请好友一起投资这个优质资产，共同见证财富增长！您的专属链接，助力朋友也能抓住这个机会！"
        ]
        
        # 如果文件存在，从文件读取文案
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
                    if messages and isinstance(messages, list) and len(messages) > 0:
                        # 随机选择一条文案
                        message = random.choice(messages)
                        return jsonify({
                            'success': True,
                            'message': message
                        }), 200
            except Exception as e:
                current_app.logger.error(f'读取分享文案文件失败: {str(e)}')
        
        # 如果文件不存在或读取失败，使用默认文案
        message = random.choice(default_messages)
        return jsonify({
            'success': True,
            'message': message
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'获取随机分享文案失败: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e),
            'message': "发现好机会就要分享！邀请好友一起投资这个优质资产！" # 兜底文案
        }), 200  # 返回200而不是500，让前端能正常处理

@api_bp.route('/upload-images', methods=['POST'])
def upload_images_api():
    """上传图片API，支持多图片上传"""
    try:
        from flask import request, current_app, jsonify
        import os
        from werkzeug.utils import secure_filename
        import time
        
        current_app.logger.info("接收到图片上传请求")
        
        if 'file0' not in request.files:
            current_app.logger.error("没有接收到图片文件")
            return jsonify({
                'success': False,
                'message': '没有接收到图片文件'
            }), 400
            
        # 获取token_symbol，用于创建正确的目录结构
        token_symbol = request.form.get('token_symbol', '')
        current_app.logger.info(f"上传图片的token_symbol: {token_symbol}")
        
        # 确定存储路径
        if token_symbol:
            # 使用新的目录结构: /static/uploads/projects/{token_symbol}/images/
            upload_folder = os.path.join(
                current_app.static_folder, 
                'uploads', 
                'projects',
                token_symbol,
                'images'
            )
        else:
            # 使用临时目录
            current_app.logger.warning("未提供token_symbol，使用临时目录")
            upload_folder = os.path.join(current_app.static_folder, 'uploads', 'temp', 'images')
            
        # 确保目录存在
        os.makedirs(upload_folder, exist_ok=True)
        current_app.logger.info(f"图片上传目录: {upload_folder}")
        
        # 处理所有上传的图片
        image_paths = []
        timestamp = int(time.time())
        
        for key in request.files:
            file = request.files[key]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # 添加时间戳防止文件名冲突
                filename = f"{timestamp}_{filename}"
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                current_app.logger.info(f"保存图片: {file_path}")
                
                # 构建相对路径，用于前端显示
                if token_symbol:
                    # 使用代理路径
                    relative_path = f"projects/{token_symbol}/images/{filename}"
                else:
                    relative_path = f"temp/images/{filename}"
                    
                image_paths.append(relative_path)
                current_app.logger.info(f"图片相对路径: {relative_path}")
        
        current_app.logger.info(f"成功上传 {len(image_paths)} 张图片")
        return jsonify({
            'success': True,
            'message': f'成功上传 {len(image_paths)} 张图片',
            'image_paths': image_paths
        })
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"上传图片失败: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'上传图片失败: {str(e)}'
        }), 500

@api_bp.route('/assets/<int:asset_id>/payment', methods=['POST'])
@eth_address_required
def process_asset_payment(asset_id):
    """处理资产支付"""
    try:
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'error': '请先连接钱包'}), 401
            
        # 获取资产信息
        asset = Asset.query.get_or_404(asset_id)
        
        # 验证请求者是资产创建者
        if asset.creator_address != g.eth_address:
            current_app.logger.warning(f"非资产创建者尝试处理支付: {g.eth_address}, 资产ID: {asset_id}")
            return jsonify({'error': '只有资产创建者可以处理支付'}), 403
            
        # 获取支付数据
        payment_data = request.json
        if not payment_data:
            return jsonify({'error': '无效的支付数据'}), 400
            
        current_app.logger.info(f"处理资产支付: {asset_id}, 数据: {payment_data}")
        
        # 验证支付数据
        required_fields = ['amount', 'status', 'transaction_id']
        for field in required_fields:
            if field not in payment_data:
                return jsonify({'error': f'缺少支付字段: {field}'}), 400
                
        # 检查支付状态
        if payment_data.get('status') != 'confirmed':
            return jsonify({'error': '支付未确认'}), 400
            
        # 检查支付金额
        min_amount = float(os.environ.get('MIN_PAYMENT_AMOUNT', 100))
        amount = float(payment_data.get('amount', 0))
        if amount < min_amount:
            return jsonify({'error': f'支付金额不足，最小金额: {min_amount} USDC'}), 400
            
        # 记录支付信息
        asset.payment_details = json.dumps(payment_data)
        asset.payment_confirmed = True
        asset.payment_confirmed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '支付处理成功'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"处理资产支付失败: {str(e)}")
        return jsonify({'error': f'处理支付失败: {str(e)}'}), 500

@api_bp.route('/assets/<int:asset_id>/deploy', methods=['POST'])
@eth_address_required
def deploy_asset_to_blockchain(asset_id):
    """部署资产到区块链"""
    try:
        # 导入资产服务
        from app.blockchain import AssetService
        
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'error': '请先连接钱包'}), 401
            
        # 获取资产信息
        asset = Asset.query.get_or_404(asset_id)
        
        # 验证请求者是资产创建者
        if asset.creator_address != g.eth_address:
            current_app.logger.warning(f"非资产创建者尝试上链: {g.eth_address}, 资产ID: {asset_id}")
            return jsonify({'error': '只有资产创建者可以部署资产'}), 403
            
        # 检查资产是否已经上链
        if asset.token_address:
            current_app.logger.info(f"资产已经上链: {asset_id}, 代币地址: {asset.token_address}")
            return jsonify({
                'success': True,
                'already_deployed': True,
                'token_address': asset.token_address,
                'message': '资产已经上链'
            })
            
        # 检查支付状态
        if not asset.payment_confirmed:
            current_app.logger.warning(f"尝试上链未支付的资产: {asset_id}")
            return jsonify({'error': '资产未完成支付，无法上链'}), 400
            
        current_app.logger.info(f"开始将资产部署到区块链: {asset_id}")
        
        # 创建资产服务实例
        asset_service = AssetService()
        
        # 部署资产
        deploy_result = asset_service.deploy_asset_to_blockchain(asset_id)
        
        if not deploy_result.get('success', False):
            return jsonify({
                'success': False,
                'error': deploy_result.get('error', '部署失败')
            }), 500
            
        return jsonify({
            'success': True,
            'token_address': deploy_result.get('token_address'),
            'details': deploy_result.get('details', {}),
            'message': '资产成功上链'
        })
    except Exception as e:
        current_app.logger.error(f"部署资产到区块链失败: {str(e)}")
        return jsonify({'error': f'部署资产失败: {str(e)}'}), 500

@api_bp.route('/service/wallet/status')
@eth_address_required
def check_service_wallet_status():
    """检查服务钱包状态"""
    try:
        from app.blockchain import AssetService
        
        # 获取钱包状态
        status = AssetService.get_service_wallet_status()
        
        # 检查是否需要设置提示
        if not status.get('success', False) and status.get('needs_setup', False):
            # 添加帮助信息
            status['setup_help'] = {
                'instructions': '请确保在.env文件中正确配置了SOLANA_SERVICE_WALLET_MNEMONIC或SOLANA_SERVICE_WALLET_PRIVATE_KEY',
                'example_env': 'SOLANA_NETWORK_URL=https://api.mainnet-beta.solana.com\nSOLANA_SERVICE_WALLET_MNEMONIC=word1 word2 ... word12',
                'found_env_vars': status.get('env_vars_found', [])
            }
        
        return jsonify(status)
    except Exception as e:
        current_app.logger.error(f"检查服务钱包状态失败: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'检查钱包状态失败: {str(e)}',
            'setup_help': {
                'instructions': '发生异常。请确保正确安装了所有依赖: mnemonic、bip32utils、base58',
                'command': 'pip install mnemonic==0.20 bip32utils==0.3.post4 base58==2.1.1'
            }
        }), 500

@api_bp.route('/generate-token-symbol', methods=['POST'])
def generate_token_symbol_api():
    """生成代币代码"""
    try:
        from app.models.asset import Asset
        
        data = request.get_json()
        asset_type = data.get('type')
        
        if not asset_type:
            return jsonify({'success': False, 'error': '缺少资产类型'}), 400
            
        # 生成随机数
        random_num = f"{random.randint(0, 9999):04d}"
        token_symbol = f"RH-{asset_type}{random_num}"
        
        # 检查是否已存在
        existing_asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if existing_asset:
            # 如果已存在，再尝试生成一次
            random_num = f"{random.randint(0, 9999):04d}"
            token_symbol = f"RH-{asset_type}{random_num}"
            
            # 再次检查
            existing_asset = Asset.query.filter_by(token_symbol=token_symbol).first()
            if existing_asset:
                return jsonify({
                    'success': False,
                    'error': '无法生成唯一的代币符号，请稍后重试'
                }), 500
        
        return jsonify({
            'success': True,
            'token_symbol': token_symbol
        })
    except Exception as e:
        current_app.logger.error(f'生成代币代码失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/assets/<int:asset_id>/distribute_dividend', methods=['POST'])
@eth_address_required
def distribute_dividend(asset_id):
    """分发资产分红，但排除发行者持有的代币"""
    try:
        # 验证请求数据
        data = request.get_json()
        if not data or 'amount' not in data:
            return jsonify({'success': False, 'error': '请提供分红金额'}), 400
            
        amount = float(data.get('amount', 0))
        if amount <= 0:
            return jsonify({'success': False, 'error': '分红金额必须大于0'}), 400
            
        # 获取发起请求的钱包地址
        user_address = g.eth_address
        
        # 获取资产信息
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({'success': False, 'error': '资产不存在'}), 404
            
        # 检查分红权限（只有管理员或资产所有者可以分红）
        is_admin_user = is_admin(user_address)
        is_asset_owner = is_same_wallet_address(asset.creator_address, user_address)
        
        if not (is_admin_user or is_asset_owner):
            return jsonify({'success': False, 'error': '您没有权限为此资产分发分红'}), 403
        
        # 获取代币持有人信息（此处通常会从区块链上查询）
        # 这里假设有一个从区块链获取持有人信息的函数
        try:
            # 实现从区块链获取持有人信息的逻辑
            # 例如: holders = solana_client.get_token_holders(asset.token_address)
            
            # 由于没有具体实现，这里模拟一个示例数据
            # 在实际实现中，这部分应替换为真实的查询逻辑
            holders = [
                {'address': 'wallet1', 'balance': 100},
                {'address': 'wallet2', 'balance': 200},
                {'address': 'wallet3', 'balance': 300},
                {'address': asset.creator_address, 'balance': asset.remaining_supply},  # 发行者持有的剩余代币
            ]
            
            # 计算总流通代币数量（排除发行者持有的代币）
            total_circulating_supply = 0
            filtered_holders = []
            
            for holder in holders:
                # 如果持有人不是发行者，则计入流通代币
                if not is_same_wallet_address(holder['address'], asset.creator_address):
                    total_circulating_supply += holder['balance']
                    filtered_holders.append(holder)
            
            # 如果没有流通代币，则返回错误
            if total_circulating_supply == 0:
                return jsonify({'success': False, 'error': '没有流通代币，无法分红'}), 400
                
            # 计算每个代币的分红金额
            dividend_per_token = amount / total_circulating_supply
            
            # 为每个持有人（除发行者外）计算分红金额
            dividend_distributions = []
            for holder in filtered_holders:
                holder_amount = holder['balance'] * dividend_per_token
                dividend_distributions.append({
                    'address': holder['address'],
                    'amount': holder_amount,
                    'token_count': holder['balance']
                })
                
            # 创建分红记录
            dividend_record = DividendRecord(
                asset_id=asset.id,
                amount=amount,
                token_price=asset.token_price,
                distributor_address=user_address,
                holders_count=len(filtered_holders),
                transaction_hash="记录已创建，等待上链确认",  # 实际中这会在上链后更新
                details=json.dumps({
                    'distributions': dividend_distributions,
                    'dividend_per_token': dividend_per_token,
                    'total_circulating_supply': total_circulating_supply
                })
            )
            
            db.session.add(dividend_record)
            db.session.commit()
            
            # 这里应该有调用区块链接口实际执行分红的逻辑
            # 例如: solana_client.distribute_dividend(asset.token_address, dividend_distributions)
            
            # 记录平台分红手续费（如果有）
            fee_percentage = 1.0  # 假设手续费是1%
            fee_amount = amount * (fee_percentage / 100)
            record_income(IncomeType.DIVIDEND, fee_amount, f"资产{asset.token_symbol}分红手续费")
            
            return jsonify({
                'success': True,
                'message': f'成功分发{amount}单位的分红至{len(filtered_holders)}个地址',
                'dividend_record_id': dividend_record.id,
                'details': {
                    'total_amount': amount,
                    'dividend_per_token': dividend_per_token,
                    'holders_count': len(filtered_holders),
                    'total_circulating_supply': total_circulating_supply,
                    'excluded_supply': asset.remaining_supply
                }
            })
            
        except Exception as e:
            current_app.logger.error(f"获取代币持有人信息失败: {str(e)}")
            return jsonify({'success': False, 'error': f'获取代币持有人信息失败: {str(e)}'}), 500
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"分发分红失败: {str(e)}")
        return jsonify({'success': False, 'error': f'分发分红失败: {str(e)}'}), 500

# 添加通过token_symbol访问的端点
@api_bp.route('/assets/symbol/<string:token_symbol>/distribute_dividend', methods=['POST'])
@eth_address_required
def distribute_dividend_by_symbol(token_symbol):
    """通过代币符号分发资产分红（重定向到ID版本）"""
    asset = Asset.query.filter_by(token_symbol=token_symbol).first()
    if not asset:
        return jsonify({'success': False, 'error': '资产不存在'}), 404
        
    return distribute_dividend(asset.id)

# 保留原有的用户资产API（使用请求头/认证中间件）
@api_bp.route('/user/assets/auth')
@eth_address_required
def get_user_assets():
    """获取用户持有的资产数据（使用eth_address_required中间件）"""
    try:
        # 获取用户地址
        user_address = g.eth_address
        
        # 记录当前请求的钱包地址，用于调试
        current_app.logger.info(f'正在为钱包地址获取资产: {user_address} (通过认证)')
        
        # 根据地址类型处理
        if user_address.startswith('0x'):
            # ETH地址，查询原始大小写地址和小写地址
            completed_trades = Trade.query.filter(
                Trade.trader_address.in_([user_address, user_address.lower()]),
                Trade.status == TradeStatus.COMPLETED.value
            ).all()
        else:
            # SOL地址或其他类型，查询原始地址（区分大小写）
            try:
                completed_trades = Trade.query.filter_by(
                    trader_address=user_address,
                    status=TradeStatus.COMPLETED.value
                ).all()
            except Exception as db_error:
                current_app.logger.error(f'数据库查询失败: {str(db_error)}', exc_info=True)
                # 返回空数组而不是抛出错误
                return jsonify([]), 200
        
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
            except Exception as asset_error:
                current_app.logger.error(f'处理资产 {asset_id} 时发生错误: {str(asset_error)}', exc_info=True)
                continue
        
        # 按持有价值降序排序
        user_assets.sort(key=lambda x: x['total_value'], reverse=True)
        
        return jsonify(user_assets), 200
    except Exception as e:
        current_app.logger.error(f'获取用户资产失败: {str(e)}', exc_info=True)
        # 返回空数组和200状态码，而不是500错误
        return jsonify([]), 200
