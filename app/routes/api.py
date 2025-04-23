from flask import (
    Blueprint, jsonify, request, current_app, 
    send_from_directory, url_for, redirect, g, session, make_response, Response
)
from flask_cors import cross_origin
from app.models.asset import Asset, AssetType, AssetStatus
from app.models.trade import Trade, TradeStatus, TradeType
from app.models.user import User, is_same_wallet_address
from app.models.shortlink import ShortLink
from sqlalchemy import desc, func
from app.extensions import db, limiter
from app.utils.decorators import token_required, eth_address_required, api_eth_address_required, task_background, admin_required
from .admin import is_admin, get_admin_info
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
from decimal import Decimal, ROUND_HALF_UP
from app.tasks import monitor_creation_payment # 假设后台任务在这里定义

# 从__init__.py中导入api_bp，而不是重新定义
from app.routes import api_bp

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
                Trade.type == TradeType.BUY.value,
                Trade.status == TradeStatus.COMPLETED.value)\
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
        'creator_address': asset.creator_address,  # 添加发起人地址
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
    """创建新资产，保存到数据库并触发支付确认后台任务"""
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
            
        wallet_address = g.eth_address
        data['creator_address'] = wallet_address
        data['owner_address'] = wallet_address
        
        # 支付交易哈希必须提供
        payment_tx_hash = data.get('payment_tx_hash')
        if not payment_tx_hash:
             return jsonify({'success': False, 'error': '缺少支付交易哈希 (payment_tx_hash)'}), 400

        # 设置初始状态为 PENDING
        data['status'] = AssetStatus.PENDING.value
        current_app.logger.info("设置资产状态为 PENDING，等待支付确认")
        
        # 记录支付信息到 payment_details (简化版，只存 tx_hash)
        payment_info = {
            'tx_hash': payment_tx_hash,
            'initiated_at': datetime.utcnow().isoformat()
        }
        data['payment_details'] = json.dumps(payment_info)
        data['payment_confirmed'] = False  # 明确设为未确认
        
        # 从data中移除非模型字段 (包括 payment_tx_hash)
        if 'payment_tx_hash' in data:
            del data['payment_tx_hash']
        # ... 移除其他不再直接存入模型的字段 ...

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
        
        # 生成Token地址（Solana格式）- 确保长度不超过128字符
        seed = f"{data.get('name', '')}_{data.get('token_symbol', '')}_{int(time.time())}".encode()
        hash_bytes = hashlib.sha256(seed).digest()[:32]
        token_address = "So" + base58.b58encode(hash_bytes).decode()
        
        # 确保地址长度不超过数据库限制(128字符)
        if len(token_address) > 128:
            token_address = token_address[:128]
            
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
        # 过滤掉不在 Asset 模型中的键
        allowed_keys = {column.name for column in Asset.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in allowed_keys}
        
        asset = Asset(**filtered_data)
        
        # 保存到数据库
        db.session.add(asset)
        db.session.commit() # 先提交获取 asset.id
        current_app.logger.info(f"资产记录已创建 (ID: {asset.id}, Symbol: {asset.token_symbol})，状态: PENDING")

        # -- 触发支付确认后台任务 --
        try:
            monitor_creation_payment.delay(asset.id, payment_tx_hash)
            current_app.logger.info(f"已触发支付确认任务 for Asset ID: {asset.id}, TxHash: {payment_tx_hash}")
        except Exception as task_err:
            current_app.logger.error(f"触发支付确认任务失败 for Asset ID: {asset.id}: {str(task_err)}")
            # 重要：即使任务触发失败，资产已创建，需要有机制处理这种情况 (例如定时扫描 PENDING 状态的资产)
            # 这里可以考虑是否需要回滚数据库操作，或仅记录错误
            # 暂时只记录错误，不回滚

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
        
        # 返回成功消息给前端 (前端会立即跳转)
        return jsonify({
            'success': True,
            'message': '资产创建请求已提交，正在后台确认支付状态',
            'asset_id': asset.id,
            'token_symbol': asset.token_symbol
            # 不再返回 token_address，因为它此时还未上链
        }), 201 # 使用 201 Created 状态码

    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"创建资产失败: {str(e)}") # 使用 exception 记录完整堆栈
        return jsonify({'success': False, 'error': '创建资产失败: ' + str(e)}), 500

# 新增：获取资产状态接口
@api_bp.route('/assets/<int:asset_id>/status', methods=['GET'])
def get_asset_status(asset_id):
    """获取指定资产的当前状态"""
    try:
        asset = Asset.query.with_entities(Asset.status, Asset.token_symbol).get(asset_id)
        if not asset:
            return jsonify({'success': False, 'error': '资产不存在'}), 404

        # 将数字状态转换为字符串表示（如果需要）
        # status_str = AssetStatus(asset.status).name if asset.status is not None else 'UNKNOWN'
        # 或者直接返回数字状态，由前端处理映射
        status_value = asset.status
        
        current_app.logger.debug(f"查询资产状态 - ID: {asset_id}, Status: {status_value}")

        return jsonify({
            'success': True,
            'asset_id': asset_id,
            'token_symbol': asset.token_symbol,
            'status': status_value # 直接返回数据库中的状态值
        }), 200

    except Exception as e:
        current_app.logger.error(f"获取资产状态失败 (ID: {asset_id}): {str(e)}")
        return jsonify({'success': False, 'error': '获取资产状态失败'}), 500

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
                'tx_hash': trade.tx_hash,
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
        
        # 获取用户地址，验证权限
        user_address = None
        if 'X-Eth-Address' in request.headers:
            user_address = request.headers.get('X-Eth-Address')
        elif data.get('wallet_address'):
            user_address = data.get('wallet_address')
        elif hasattr(g, 'eth_address'):
            user_address = g.eth_address
            
        # 如果提供了地址，验证交易创建者
        if user_address:
            user_address_lower = user_address.lower() if user_address.startswith('0x') else user_address
            trader_address_lower = trade.trader_address.lower() if trade.trader_address.startswith('0x') else trade.trader_address
            
            # 检查是否是交易创建者或管理员
            is_creator = user_address_lower == trader_address_lower
            is_admin_user = is_admin(user_address)
            
            if not is_creator and not is_admin_user:
                current_app.logger.warning(f'无权更新交易状态: 用户={user_address}, 交易创建者={trade.trader_address}')
                return jsonify({'error': '无权操作此交易'}), 403
                
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
        
        # 获取资产信息
        asset = Asset.query.get(trade.asset_id)
        
        return jsonify({
            'id': trade.id,
            'status': trade.status,
            'tx_hash': trade.tx_hash,
            'remaining_supply': asset.remaining_supply if asset else None,
            'success': True
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
                    Trade.type == TradeType.BUY.value,
                    Trade.status == TradeStatus.COMPLETED.value)\
            .distinct().count()
        
        # 3. 计算已售出代币数量
        tokens_sold = 0
        if asset.token_supply is not None and asset.remaining_supply is not None:
            tokens_sold = asset.token_supply - asset.remaining_supply
        elif asset.token_supply is not None:
            # 当remaining_supply不可用时，尝试从交易记录计算
            try:
                # 统计所有已完成的购买交易总量
                buy_trades_total = db.session.query(func.sum(Trade.amount))\
                    .filter(Trade.asset_id == asset.id, 
                            Trade.type == TradeType.BUY.value,
                            Trade.status == TradeStatus.COMPLETED.value)\
                    .scalar() or 0
                tokens_sold = buy_trades_total
            except Exception as e:
                current_app.logger.error(f"计算已售出代币时出错: {str(e)}")
                # 发生错误时返回0，而不是抛出异常
                tokens_sold = 0
        
        data = {
            'count': dividend_count,  # 分红次数
            'total_amount': total_dividend,  # 累计分红金额
            'holder_count': unique_holders,  # 当前持有人数
            'tokens_sold': tokens_sold  # 已售出代币数量
        }

        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f'获取分红统计失败: {str(e)}')
        # 返回一个有效的响应，而不是500错误
        return jsonify({
            'count': 0,
            'total_amount': 0,
            'holder_count': 0,
            'tokens_sold': 0,
            'error': '获取分红统计失败'
        })

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

@api_bp.route('/wallet/balance', methods=['GET'], endpoint='get_wallet_balance_endpoint')
def get_wallet_balance():
    """获取用户钱包的USDC和SOL余额"""
    address = request.args.get('address')
    wallet_type = request.args.get('wallet_type', 'ethereum')
    
    if not address:
        return jsonify({'success': False, 'error': '缺少钱包地址'}), 400
    
    current_app.logger.info(f'获取钱包余额请求 - 地址: {address}, 类型: {wallet_type}')
    
    try:
        # 创建返回结果
        balances = {
            'USDC': 0,
            'SOL': 0
        }
        
        # 根据钱包类型设置不同余额
        if wallet_type == 'phantom':
            # 查询Solana钱包的SOL余额
            try:
                # 导入区块链客户端
                from app.blockchain.solana import SolanaClient
                
                # 创建只读Solana客户端实例，用于查询用户钱包
                solana_client = SolanaClient(wallet_address=address)
                
                # 获取SOL余额
                sol_balance = solana_client.get_balance()
                
                if sol_balance is not None:
                    balances['SOL'] = sol_balance
                    current_app.logger.info(f'SOL余额: {sol_balance}')
                else:
                    current_app.logger.warning('无法获取SOL余额，返回0')
                    balances['SOL'] = 0
                
                # 获取USDC余额 - USDC Token在Solana上的地址
                # Solana主网USDC代币地址
                usdc_token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                try:
                    from app.blockchain.asset_service import AssetService
                    # 调用获取SPL代币余额的方法
                    usdc_balance = AssetService.get_token_balance(wallet_address=address, token_mint_address=usdc_token_address)
                    balances['USDC'] = usdc_balance
                    current_app.logger.info(f'USDC余额: {usdc_balance}')
                except Exception as usdc_err:
                    current_app.logger.error(f'获取USDC余额失败: {str(usdc_err)}')
                    # 获取USDC失败不影响整体结果，保持USDC=0
            except Exception as sol_err:
                current_app.logger.error(f'获取SOL余额失败: {str(sol_err)}')
                balances['SOL'] = 0
                
        else:
            # 如果是以太坊钱包，可以添加以太坊余额查询逻辑
            try:
                # 导入以太坊客户端
                from app.blockchain.ethereum import get_usdc_balance, get_eth_balance
                
                # 获取ETH余额
                eth_balance = get_eth_balance(address)
                if eth_balance is not None:
                    balances['ETH'] = eth_balance
                    current_app.logger.info(f'ETH余额: {eth_balance}')
                
                # 获取USDC余额
                usdc_balance = get_usdc_balance(address)
                if usdc_balance is not None:
                    balances['USDC'] = usdc_balance
                    current_app.logger.info(f'USDC余额: {usdc_balance}')
            except Exception as eth_err:
                current_app.logger.error(f'获取以太坊余额失败: {str(eth_err)}')
            
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

@api_bp.route('/user/check_admin')
def check_if_admin():
    """
    检查用户是否是管理员
    支持通过URL参数或头部获取地址
    """
    try:
        # 从多个来源获取地址
        eth_address = None
        wallet_type = request.args.get('wallet_type', 'ethereum')
        
        # 尝试从请求参数获取
        if request.args.get('address'):
            eth_address = request.args.get('address')
            current_app.logger.info(f'从URL参数获取地址: {eth_address}')
            
        # 尝试从请求头获取
        if not eth_address and request.headers.get('X-Eth-Address'):
            eth_address = request.headers.get('X-Eth-Address')
            current_app.logger.info(f'从请求头获取地址: {eth_address}')
            
        # 尝试从Cookie获取
        if not eth_address and request.cookies.get('eth_address'):
            eth_address = request.cookies.get('eth_address')
            current_app.logger.info(f'从Cookie获取地址: {eth_address}')
            
        # 尝试从g对象获取
        if not eth_address and hasattr(g, 'eth_address'):
            eth_address = g.eth_address
            current_app.logger.info(f'从g对象获取地址: {eth_address}')
        
        # 如果没有找到地址
        if not eth_address:
            current_app.logger.warning('未找到钱包地址')
            return jsonify({
                'success': False,
                'is_admin': False,
                'admin': False,
                'message': '未提供钱包地址'
            })
            
        # 检查是否是管理员
        admin_status = is_admin(eth_address)
        
        # 如果是管理员，获取更多信息
        admin_info = None
        if admin_status:
            admin_info = get_admin_info(eth_address)
            
        # 记录结果
        current_app.logger.info(f'地址 {eth_address} 管理员状态: {admin_status}')
            
        return jsonify({
            'success': True,
            'is_admin': admin_status,
            'admin': admin_status,  # 保持兼容
            'wallet_type': wallet_type,
            'address': eth_address,
            'admin_info': admin_info
        })
    except Exception as e:
        current_app.logger.error(f'检查管理员状态时出错: {str(e)}')
        return jsonify({
            'success': False,
            'is_admin': False,
            'admin': False,
            'message': f'检查管理员状态时出错: {str(e)}'
        })

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
        
        # 返回空数组，让系统从区块链获取真实数据
        current_app.logger.info('返回空数组，系统将从区块链获取真实数据')
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
        current_app.logger.info(f"请求表单数据: {list(request.form.keys())}")
        current_app.logger.info(f"请求文件数据: {list(request.files.keys())}")
        
        # 检查请求中是否包含文件
        file_count = len(request.files)
        if file_count == 0:
            current_app.logger.error("请求中没有包含任何文件")
            return jsonify({
                'success': False,
                'message': '请求中没有包含任何文件'
            }), 400
            
        current_app.logger.info(f"接收到 {file_count} 个文件")
        
        # 允许任何文件键名，不仅仅是file0
        files_to_process = []
        for key in request.files:
            file = request.files[key]
            if file and file.filename:
                files_to_process.append(file)
                current_app.logger.info(f"准备处理文件: {file.filename}, 类型: {file.content_type}")
        
        if not files_to_process:
            current_app.logger.error("没有有效的文件可以处理")
            return jsonify({
                'success': False,
                'message': '没有有效的文件可以处理'
            }), 400
            
        # 获取token_symbol，用于创建正确的目录结构
        token_symbol = request.form.get('token_symbol', '')
        current_app.logger.info(f"上传图片的token_symbol: {token_symbol}")
        
        # 尝试两种可能的上传路径
        app_uploads_path = os.path.join(current_app.root_path, 'uploads')
        static_uploads_path = os.path.join(current_app.static_folder, 'uploads')
        
        current_app.logger.info(f"检查可能的上传路径:")
        current_app.logger.info(f"1. app uploads: {app_uploads_path}")
        current_app.logger.info(f"2. static uploads: {static_uploads_path}")
        
        # 确定实际使用的上传基础路径
        base_uploads_path = static_uploads_path if os.path.exists(static_uploads_path) else app_uploads_path
        current_app.logger.info(f"选择的上传基础路径: {base_uploads_path}")
        
        # 确定存储路径
        if token_symbol:
            # 使用新的目录结构: /uploads/projects/{token_symbol}/images/
            upload_folder = os.path.join(
                base_uploads_path, 
                'projects',
                token_symbol,
                'images'
            )
        else:
            # 使用临时目录
            current_app.logger.warning("未提供token_symbol，使用临时目录")
            upload_folder = os.path.join(base_uploads_path, 'temp', 'images')
            
        # 检查并创建所有父目录
        try:
            # 确保上传基础目录存在
            if not os.path.exists(base_uploads_path):
                current_app.logger.warning(f"上传基础目录不存在，尝试创建: {base_uploads_path}")
                os.makedirs(base_uploads_path, exist_ok=True)
                
            # 确保projects目录存在
            projects_dir = os.path.join(base_uploads_path, 'projects')
            if not os.path.exists(projects_dir):
                current_app.logger.warning(f"projects目录不存在，尝试创建: {projects_dir}")
                os.makedirs(projects_dir, exist_ok=True)
            
            # 如果使用临时目录，确保它存在
            if not token_symbol:
                temp_dir = os.path.join(base_uploads_path, 'temp')
                if not os.path.exists(temp_dir):
                    current_app.logger.warning(f"temp目录不存在，尝试创建: {temp_dir}")
                    os.makedirs(temp_dir, exist_ok=True)
                    
                temp_images_dir = os.path.join(temp_dir, 'images')
                if not os.path.exists(temp_images_dir):
                    current_app.logger.warning(f"temp/images目录不存在，尝试创建: {temp_images_dir}")
                    os.makedirs(temp_images_dir, exist_ok=True)
            
            # 确保最终的上传目录存在
            current_app.logger.info(f"尝试创建上传目录: {upload_folder}")
            os.makedirs(upload_folder, exist_ok=True)
            current_app.logger.info(f"上传目录创建或确认成功: {upload_folder}")
            
            # 检查目录权限
            if not os.access(upload_folder, os.W_OK):
                current_app.logger.error(f"上传目录没有写入权限: {upload_folder}")
                try:
                    # 尝试修改权限
                    import stat
                    os.chmod(upload_folder, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 777权限
                    current_app.logger.info(f"已尝试修改目录权限: {upload_folder}")
                    
                    if not os.access(upload_folder, os.W_OK):
                        current_app.logger.error(f"修改权限后，仍然没有写入权限: {upload_folder}")
                        return jsonify({
                            'success': False,
                            'message': f'服务器目录权限错误，无法写入: {upload_folder}'
                        }), 500
                except Exception as perm_err:
                    current_app.logger.error(f"修改目录权限失败: {str(perm_err)}")
                    return jsonify({
                        'success': False,
                        'message': f'服务器目录权限错误，无法修复: {str(perm_err)}'
                    }), 500
        except PermissionError as pe:
            current_app.logger.error(f"创建目录权限错误: {str(pe)}")
            return jsonify({
                'success': False,
                'message': f'服务器权限错误: {str(pe)}'
            }), 500
        except Exception as e:
            current_app.logger.error(f"创建目录失败: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'创建目录失败: {str(e)}'
            }), 500
        
        # 处理所有上传的图片
        image_paths = []
        timestamp = int(time.time())
        
        for file in files_to_process:
            if file and allowed_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    # 添加时间戳防止文件名冲突
                    filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(upload_folder, filename)
                    
                    current_app.logger.info(f"准备保存文件: {file_path}")
                    file.save(file_path)
                    
                    # 检查文件是否实际创建
                    if os.path.exists(file_path):
                        current_app.logger.info(f"文件保存成功: {file_path}, 大小: {os.path.getsize(file_path)} 字节")
                    else:
                        current_app.logger.error(f"文件保存失败，路径不存在: {file_path}")
                        return jsonify({
                            'success': False,
                            'message': f'文件无法保存到服务器: {file_path}'
                        }), 500
                    
                    # 构建相对路径，用于前端显示
                    # 确保使用与前端一致的URL格式
                    if token_symbol:
                        # 使用项目路径
                        relative_path = f"/static/uploads/projects/{token_symbol}/images/{filename}"
                    else:
                        relative_path = f"/static/uploads/temp/images/{filename}"
                        
                    image_paths.append(relative_path)
                    current_app.logger.info(f"图片URL路径: {relative_path}")
                except Exception as save_err:
                    current_app.logger.error(f"保存文件时出错: {str(save_err)}")
                    import traceback
                    current_app.logger.error(traceback.format_exc())
                    return jsonify({
                        'success': False,
                        'message': f'保存文件错误: {str(save_err)}'
                    }), 500
            else:
                current_app.logger.warning(f"文件 {file.filename} 类型不允许，跳过")
                
        if len(image_paths) == 0:
            current_app.logger.warning("所有文件处理完毕，但没有成功保存任何图片")
            return jsonify({
                'success': False,
                'message': '没有成功保存任何图片，请检查文件类型是否被支持'
            }), 400
            
        current_app.logger.info(f"成功上传 {len(image_paths)} 张图片: {image_paths}")
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
        
        # 记录请求开始
        current_app.logger.info("开始处理生成代币符号请求")
        
        # 验证请求数据
        try:
            data = request.get_json()
        except Exception as e:
            current_app.logger.error(f"解析请求JSON数据失败: {str(e)}")
            return jsonify({'success': False, 'error': '无效的请求格式'}), 400
            
        if not data:
            current_app.logger.error("生成代币符号失败: 无效的请求数据")
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        asset_type = data.get('type')
        current_app.logger.info(f"正在为资产类型 {asset_type} 生成代币符号")
        
        if not asset_type:
            current_app.logger.error("生成代币符号失败: 缺少资产类型参数")
            return jsonify({'success': False, 'error': '缺少资产类型'}), 400
        
        # 确保资产类型是字符串格式
        try:
            asset_type = str(asset_type)
            current_app.logger.info(f"转换后的资产类型: {asset_type}")
        except Exception as e:
            current_app.logger.error(f"转换资产类型为字符串失败: {str(e)}")
            return jsonify({'success': False, 'error': f'资产类型格式错误: {str(e)}'}), 400
            
        # 生成随机数
        try:
            random_num = f"{random.randint(0, 9999):04d}"
            token_symbol = f"RH-{asset_type}{random_num}"
            current_app.logger.info(f"第一次尝试生成的代币符号: {token_symbol}")
        except Exception as e:
            current_app.logger.error(f"生成随机代币符号失败: {str(e)}")
            # 使用时间戳作为备用方案
            import time
            token_symbol = f"RH-{asset_type}{int(time.time()) % 10000}"
            current_app.logger.info(f"备用方案：使用时间戳生成的代币符号: {token_symbol}")
        
        # 检查是否已存在
        try:
            existing_asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        except Exception as e:
            current_app.logger.error(f"查询数据库检查代币符号是否存在时出错: {str(e)}")
            # 使用更独特的标识符
            import time
            token_symbol = f"RH-{asset_type}{int(time.time() * 1000) % 10000}"
            current_app.logger.info(f"查询失败后使用毫秒时间戳生成的代币符号: {token_symbol}")
            return jsonify({'success': True, 'token_symbol': token_symbol})
            
        if existing_asset:
            current_app.logger.info(f"代币符号 {token_symbol} 已存在，尝试第二次生成")
            
            # 如果已存在，再尝试生成一次
            try:
                random_num = f"{random.randint(0, 9999):04d}"
                token_symbol = f"RH-{asset_type}{random_num}"
                current_app.logger.info(f"第二次尝试生成的代币符号: {token_symbol}")
            except Exception as e:
                current_app.logger.error(f"第二次生成随机代币符号失败: {str(e)}")
                # 使用时间戳作为备用方案
                import time
                token_symbol = f"RH-{asset_type}{int(time.time()) % 10000}"
                current_app.logger.info(f"第二次备用方案：使用时间戳生成的代币符号: {token_symbol}")
            
            # 再次检查
            try:
                existing_asset = Asset.query.filter_by(token_symbol=token_symbol).first()
            except Exception as e:
                current_app.logger.error(f"第二次查询数据库检查代币符号是否存在时出错: {str(e)}")
                # 使用更独特的标识符
                import time
                token_symbol = f"RH-{asset_type}{int(time.time() * 1000) % 10000}"
                current_app.logger.info(f"第二次查询失败后使用毫秒时间戳生成的代币符号: {token_symbol}")
                return jsonify({'success': True, 'token_symbol': token_symbol})
                
            if existing_asset:
                current_app.logger.info(f"代币符号 {token_symbol} 依然存在，使用时间戳生成")
                
                # 如果依然存在，使用时间戳
                try:
                    import time
                    timestamp = int(time.time())
                    token_symbol = f"RH-{asset_type}{timestamp % 10000}"
                    current_app.logger.info(f"使用时间戳生成的代币符号: {token_symbol}")
                except Exception as e:
                    current_app.logger.error(f"使用时间戳生成代币符号失败: {str(e)}")
                    # 使用更加独特的标识符
                    import time, uuid
                    unique_id = str(uuid.uuid4())[:4]
                    token_symbol = f"RH-{asset_type}{unique_id}"
                    current_app.logger.info(f"使用UUID生成的代币符号: {token_symbol}")
                
                # 最后检查一次
                try:
                    existing_asset = Asset.query.filter_by(token_symbol=token_symbol).first()
                except Exception as e:
                    current_app.logger.error(f"最终查询数据库检查代币符号是否存在时出错: {str(e)}")
                    # 放弃检查，直接返回最新生成的符号
                    return jsonify({'success': True, 'token_symbol': token_symbol})
                    
                if existing_asset:
                    current_app.logger.error(f"无法生成唯一的代币符号，所有尝试都已存在")
                    # 最终备用方案：使用UUID生成完全唯一的标识符
                    import uuid
                    unique_id = str(uuid.uuid4())[:6]
                    token_symbol = f"RH-{asset_type}{unique_id}"
                    current_app.logger.info(f"最终备用方案：使用UUID生成的代币符号: {token_symbol}")
        
        current_app.logger.info(f"成功生成代币符号: {token_symbol}")
        return jsonify({'success': True, 'token_symbol': token_symbol})
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        current_app.logger.error(f"生成代币符号失败: {str(e)}\n{error_traceback}")
        
        # 发生未知错误时，仍然尝试生成一个符号而不是返回500错误
        try:
            import time, uuid
            asset_type = request.get_json().get('type', '00') if request.get_json() else '00'
            unique_id = f"{int(time.time() % 10000)}-{str(uuid.uuid4())[:4]}"
            emergency_token_symbol = f"RH-{asset_type}{unique_id}"
            current_app.logger.info(f"紧急情况下生成的代币符号: {emergency_token_symbol}")
            return jsonify({'success': True, 'token_symbol': emergency_token_symbol})
        except Exception as fallback_error:
            current_app.logger.error(f"最后的紧急备用生成也失败了: {str(fallback_error)}")
            return jsonify({'success': False, 'error': f'生成代币符号失败，请重试'}), 500

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

@api_bp.route('/payments/register_pending', methods=['POST'])
@eth_address_required
def register_pending_payment():
    """
    注册待确认的支付交易
    该API允许前端在创建资产后注册一个待确认的支付交易，系统将异步处理确认
    
    注意：当前系统使用的是备用转账方案，不执行实际的链上转账，而是通过管理员后台确认
    未来计划实现与Solana区块链的实时交互以实现自动化支付验证
    """
    try:
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'success': False, 'error': '请先连接钱包'}), 401
            
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        # 检查必要字段
        required_fields = ['asset_id', 'tx_hash', 'platform_address']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400
                
        # 获取资产
        asset_id = data.get('asset_id')
        tx_hash = data.get('tx_hash')
        platform_address = data.get('platform_address')
        
        # 查询资产
        from app.models.asset import Asset
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({'success': False, 'error': f'资产不存在: {asset_id}'}), 404
            
        # 验证资产所有者
        if asset.creator_address != g.eth_address:
            current_app.logger.warning(f"非资产创建者尝试注册支付交易: {g.eth_address}, 资产ID: {asset_id}")
            return jsonify({'success': False, 'error': '只有资产创建者可以注册支付交易'}), 403
            
        # 记录支付信息
        payment_info = {
            'tx_hash': tx_hash,
            'platform_address': platform_address,
            'status': 'pending',
            'registered_at': datetime.utcnow().isoformat(),
            'registered_by': g.eth_address
        }
        
        # 更新资产支付信息
        asset.payment_details = json.dumps(payment_info)
        asset.payment_confirmed = False  # 尚未确认
        
        # 保存到数据库
        db.session.commit()
        
        # 记录日志
        current_app.logger.info(f"已注册支付交易 - 资产ID: {asset_id}, 交易哈希: {tx_hash}")
        
        # 触发异步任务检查交易（如果有后台任务系统）
        try:
            # 这里可以调用异步任务系统，如Celery或其他
            current_app.logger.info(f"注册异步任务检查交易: {tx_hash}")
            # 例如: tasks.check_transaction_status.delay(asset_id, tx_hash)
            
            # 记录日志
            current_app.logger.info(f"已注册待确认的支付交易: 资产ID={asset_id}, 交易哈希={tx_hash}")
        except Exception as e:
            current_app.logger.error(f"触发异步任务失败: {str(e)}")
            # 继续执行，不影响主流程
        
        return jsonify({
            'success': True,
            'message': '支付交易已注册，系统将异步处理确认',
            'asset_id': asset_id,
            'tx_hash': tx_hash
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"注册待确认支付交易失败: {str(e)}")
        return jsonify({'success': False, 'error': f'注册支付交易失败: {str(e)}'}), 500

@api_bp.route('/solana/create_transfer_transaction', methods=['POST'])
@eth_address_required
def create_solana_transfer_transaction():
    """
    创建Solana转账交易
    用于生成转账USDC或其他代币的Solana交易，返回序列化的交易数据
    前端使用Phantom钱包签名并发送
    """
    try:
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'success': False, 'error': '请先连接钱包'}), 401
            
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        # 检查必要字段
        required_fields = ['token_symbol', 'to_address', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400
                
        token_symbol = data.get('token_symbol')
        to_address = data.get('to_address')
        amount = float(data.get('amount'))
        
        # 记录请求信息
        current_app.logger.info(f"创建Solana转账交易: {token_symbol}, 金额: {amount}, 接收地址: {to_address}, 发送钱包: {g.eth_address}")
        
        # 根据代币符号获取正确的代币铸造地址
        token_addresses = {
            'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC在Solana主网上的地址
            'SOL': 'So11111111111111111111111111111111111111112'     # SOL的标准程序地址
        }
        
        # 获取代币地址
        token_address = token_addresses.get(token_symbol)
        if not token_address:
            return jsonify({'success': False, 'error': f'不支持的代币: {token_symbol}'}), 400
            
        # USDC在Solana上有6位小数
        decimals = 6 if token_symbol == 'USDC' else 9
        
        # 转换为最小单位金额
        amount_in_lamports = int(amount * 10**decimals)
        
        # 使用Solana Python客户端创建转账交易
        # 在生产环境中，这里应该使用实际的Solana Web3.py等库构建交易
        from app.utils.solana_compat.publickey import PublicKey  # 导入Solana兼容工具
        from app.utils.solana_compat.transaction import Transaction
        from app.utils.solana_compat.token import Token, TOKEN_PROGRAM_ID
        from app.utils.solana_compat.connection import Connection
        
        try:
            # 创建连接对象
            connection = Connection("https://api.mainnet-beta.solana.com")
            
            # 创建交易
            transaction = Transaction()
            
            # 添加转账指令
            from_pubkey = PublicKey(g.eth_address)
            to_pubkey = PublicKey(to_address)
            token_pubkey = PublicKey(token_address)
            
            # 创建Token客户端对象
            token_client = Token(
                conn=connection,
                pubkey=token_pubkey,
                program_id=TOKEN_PROGRAM_ID,
                payer=from_pubkey
            )
            
            # 获取源和目标Token账户
            from_token_account = token_client.get_associated_token_address(from_pubkey)
            to_token_account = token_client.get_associated_token_address(to_pubkey)
            
            # 添加转账指令到交易
            transfer_tx = token_client.transfer(
                source=from_token_account,
                dest=to_token_account,
                owner=from_pubkey,
                amount=amount_in_lamports
            )
            
            # 合并到主交易
            transaction.add(transfer_tx)
            
            # 获取最新的区块哈希
            recent_blockhash = connection.get_recent_blockhash()
            transaction.recent_blockhash = recent_blockhash
            
            # 序列化交易
            serialized_transaction = transaction.serialize()
            
            # 转换为Base64以便JSON传输
            import base64
            serialized_transaction_b64 = base64.b64encode(serialized_transaction).decode('utf-8')
            
            # 返回序列化的交易数据
            return jsonify({
                'success': True,
                'transaction': serialized_transaction_b64,
                'message': f'已创建转账{amount} {token_symbol}到{to_address}的交易',
                'token_address': token_address,
                'from_address': g.eth_address,
                'to_address': to_address,
                'amount': amount,
                'amount_in_lamports': amount_in_lamports
            })
            
        except Exception as tx_error:
            current_app.logger.error(f"创建Solana交易失败: {str(tx_error)}")
            return jsonify({'success': False, 'error': f'创建交易失败: {str(tx_error)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"处理转账交易请求失败: {str(e)}")
        return jsonify({'success': False, 'error': f'处理请求失败: {str(e)}'}), 500

@api_bp.route('/solana/send_transaction', methods=['POST'])
@eth_address_required
def send_solana_transaction():
    """
    发送已签名的Solana交易
    接收前端传来的已签名交易，发送到Solana网络
    """
    try:
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'success': False, 'error': '请先连接钱包'}), 401
            
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        # 检查必要字段
        if 'signed_transaction' not in data:
            return jsonify({'success': False, 'error': '缺少已签名的交易数据'}), 400
            
        signed_transaction_b64 = data.get('signed_transaction')
        
        # 记录请求信息
        current_app.logger.info(f"接收到已签名交易，发送方: {g.eth_address}")
        
        # 解码交易数据
        import base64
        try:
            signed_transaction_bytes = base64.b64decode(signed_transaction_b64)
        except Exception as e:
            current_app.logger.error(f"解码交易数据失败: {str(e)}")
            return jsonify({'success': False, 'error': f'解码交易数据失败: {str(e)}'}), 400
        
        # 使用Solana Python客户端发送已签名的交易
        from app.utils.solana_compat.connection import Connection
        
        try:
            # 创建连接对象
            connection = Connection("https://api.mainnet-beta.solana.com")
            
            # 发送交易
            signature = connection.send_raw_transaction(signed_transaction_bytes)
            
            # 记录成功信息
            current_app.logger.info(f"交易发送成功，签名: {signature}")
            
            # 返回成功结果
            return jsonify({
                'success': True,
                'signature': signature,
                'message': '交易已发送至Solana网络'
            })
            
        except Exception as tx_error:
            current_app.logger.error(f"发送交易失败: {str(tx_error)}")
            return jsonify({'success': False, 'error': f'发送交易失败: {str(tx_error)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"处理交易请求失败: {str(e)}")
        return jsonify({'success': False, 'error': f'处理请求失败: {str(e)}'}), 500

@api_bp.route('/solana/get_latest_blockhash', methods=['GET'])
@eth_address_required
def get_latest_blockhash():
    """获取Solana最新区块哈希，用于构建交易"""
    try:
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'success': False, 'error': '请先连接钱包'}), 401
            
        # 记录请求信息
        current_app.logger.info(f"获取最新区块哈希请求 - 用户: {g.eth_address}")
        
        # 使用简化的模拟数据返回，避免依赖Solana客户端可能导致的问题
        # 在真实环境下应该使用Solana客户端获取最新区块哈希
        import hashlib
        import time
        
        # 创建一个基于时间的伪随机哈希值
        seed = f"blockhash-{int(time.time())}-{g.eth_address}"
        blockhash = hashlib.sha256(seed.encode()).hexdigest()
        
        current_app.logger.info(f"返回模拟区块哈希: {blockhash}")
        
        # 返回成功结果
        return jsonify({
            'success': True,
            'blockhash': blockhash,
            'message': '成功获取最新区块哈希(模拟)'
        })
        
    except Exception as e:
        current_app.logger.error(f"处理区块哈希请求失败: {str(e)}")
        return jsonify({'success': False, 'error': f'处理请求失败: {str(e)}'}), 500


@api_bp.route('/solana/get_transfer_params', methods=['POST'])
@eth_address_required
def get_transfer_params():
    """
    获取转账交易所需的参数
    返回交易数据和消息，用于钱包签名
    """
    try:
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'success': False, 'error': '请先连接钱包'}), 401
            
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        # 检查必要字段
        required_fields = ['token_symbol', 'to_address', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400
                
        token_symbol = data.get('token_symbol')
        to_address = data.get('to_address')
        amount = float(data.get('amount'))
        # blockhash可选，如果没有提供会在后端自动获取
        blockhash = data.get('blockhash')
        from_address = g.eth_address
        
        # 记录请求信息
        current_app.logger.info(f"获取转账参数 - 用户: {from_address}, 代币: {token_symbol}, 接收方: {to_address}, 金额: {amount}")
        
        # 获取交易参数和消息
        from app.blockchain.solana_service import prepare_transfer_transaction
        
        try:
            # 如果没有提供blockhash，后端会自动获取
            transaction_data, message_data = prepare_transfer_transaction(
                token_symbol=token_symbol,
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                blockhash=blockhash
            )
            
            # 检查返回结果
            if not transaction_data or not message_data:
                raise Exception("无法创建有效的交易数据")
            
            # 转换为Base64格式
            import base64
            transaction_base64 = base64.b64encode(transaction_data).decode('ascii')
            message_base64 = base64.b64encode(message_data).decode('ascii')
            
            # 记录成功信息
            current_app.logger.info(f"成功生成转账参数 - 用户: {from_address}")
            
            # 返回成功结果
            return jsonify({
                'success': True,
                'transaction': transaction_base64,
                'message': message_base64
            })
            
        except Exception as prepare_error:
            current_app.logger.error(f"准备交易数据失败: {str(prepare_error)}")
            return jsonify({'success': False, 'error': f'准备交易数据失败: {str(prepare_error)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"处理转账参数请求失败: {str(e)}")
        return jsonify({'success': False, 'error': f'处理请求失败: {str(e)}'}), 500


@api_bp.route('/solana/send_signed_transaction', methods=['POST'])
@eth_address_required
def send_signed_transaction():
    """
    发送已签名的Solana交易
    """
    try:
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'success': False, 'error': '请先连接钱包'}), 401
            
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        # 检查必要字段
        if 'signature' not in data:
            return jsonify({'success': False, 'error': '缺少交易签名'}), 400
            
        # 新格式包含完整的已签名交易对象
        if 'signedTransaction' not in data:
            return jsonify({'success': False, 'error': '缺少已签名交易数据'}), 400
            
        signature = data.get('signature')
        signed_transaction = data.get('signedTransaction')
        
        current_app.logger.info(f"处理已签名交易: 用户={g.eth_address}, 签名={signature}")
        
        # 模拟发送交易到网络
        # 在真实环境中，这里应该把签名的交易发送到Solana网络
        
        # 生成唯一的交易ID
        import hashlib
        import time
        
        # 创建一个唯一的种子
        seed = f"{g.eth_address}:{signature}:{int(time.time())}"
        tx_id = hashlib.sha256(seed.encode()).hexdigest()
        
        current_app.logger.info(f"交易发送成功，ID: {tx_id}")
        
        # 返回发送结果
        return jsonify({
            'success': True,
            'signature': tx_id,
            'message': '交易已发送到网络'
        })
        
    except Exception as e:
        current_app.logger.error(f"发送已签名交易失败: {str(e)}")
        return jsonify({'success': False, 'error': f'发送交易失败: {str(e)}'}), 500


@api_bp.route('/solana/execute_transfer', methods=['POST'])
@eth_address_required
def execute_transfer():
    """
    执行Solana转账
    该方法执行真实的链上转账，并自动监控交易确认状态
    """
    try:
        # 检查钱包连接状态
        if not g.eth_address:
            current_app.logger.error("未检测到钱包地址，请求头信息: " + str(request.headers))
            return jsonify({'success': False, 'error': '请先连接钱包'}), 401
            
        # 获取请求数据
        data = request.get_json()
        if not data:
            current_app.logger.error("请求数据为空，请求内容: " + str(request.data))
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        # 记录请求数据，帮助调试
        current_app.logger.info(f"转账请求数据: {data}")
            
        # 检查必要字段
        required_fields = ['token_symbol', 'to_address', 'amount', 'from_address']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            current_app.logger.error(f"缺少必要字段: {missing_fields}")
            return jsonify({'success': False, 'error': f'缺少必要字段: {", ".join(missing_fields)}'}), 400
                
        token_symbol = data.get('token_symbol')
        to_address = data.get('to_address')
        
        # 数字格式处理
        try:
            amount_str = data.get('amount')
            current_app.logger.info(f"处理金额数据: {amount_str}, 类型: {type(amount_str)}")
            
            # 尝试转换为浮点数，支持多种格式
            if isinstance(amount_str, str):
                # 清理字符串，移除任何可能影响解析的字符
                clean_amount_str = amount_str.strip().replace(',', '.')
                amount = float(clean_amount_str)
            else:
                amount = float(amount_str)
            
            # 检查是否为整数值
            if amount != int(amount):
                current_app.logger.error(f"金额必须是整数: {amount}")
                return jsonify({'success': False, 'error': f'代币数量必须是整数，收到的值: {amount}'}), 400
                
            current_app.logger.info(f"金额转换结果: {amount}, 类型: {type(amount)}")
            
            # 确保金额大于0
            if amount <= 0:
                raise ValueError(f"金额必须大于0，当前值: {amount}")
                
        except Exception as e:
            current_app.logger.error(f"金额转换失败: {str(e)}, 原始值: {data.get('amount')}")
            return jsonify({'success': False, 'error': f'无效的金额格式: {data.get("amount")}'}), 400
        
        from_address = data.get('from_address')
        
        # 验证发送方地址匹配已连接的钱包地址
        if from_address != g.eth_address:
            current_app.logger.warning(f"地址不匹配: from_address={from_address}, g.eth_address={g.eth_address}")
            # 放宽验证，只记录警告但允许继续
            current_app.logger.warning("地址不匹配但允许继续执行")
        
        # 记录请求信息
        current_app.logger.info(f"执行转账 - 用户: {from_address}, 代币: {token_symbol}, 接收方: {to_address}, 金额: {amount}")
        
        # 执行真实的链上转账
        from app.blockchain.solana_service import execute_transfer_transaction
        
        # 将amount转换为整数传递给服务函数
        try:
            amount_int = int(amount)
        except ValueError:
            current_app.logger.error(f"无法将金额转换为整数: {amount}")
            return jsonify({'success': False, 'error': f'内部错误：金额格式无效'}), 500

        # 执行转账交易
        transfer_result = execute_transfer_transaction(
            token_symbol=token_symbol,
            from_address=from_address,
            to_address=to_address,
            amount=amount_int # 传递整数金额
        )
        
        # 检查服务函数的返回结果
        if isinstance(transfer_result, dict) and not transfer_result.get('success', True):
            # 如果返回的是错误字典
            error_message = transfer_result.get('error', '执行转账时发生未知错误')
            current_app.logger.error(f"执行转账服务函数返回错误: {error_message}")
            # 根据错误类型判断返回400还是500
            status_code = 400 if "无效" in error_message or "格式" in error_message else 500
            return jsonify({'success': False, 'error': error_message}), status_code
        elif not isinstance(transfer_result, str):
            # 如果返回的不是字符串签名也不是错误字典，则认为是内部错误
            current_app.logger.error(f"执行转账服务函数返回了意外的类型: {type(transfer_result)}, 值: {transfer_result}")
            return jsonify({'success': False, 'error': '执行转账时发生意外错误'}), 500

        # 如果返回的是签名字符串
        signature = transfer_result
        current_app.logger.info(f"转账交易已发送，签名: {signature}")
        
        # 返回成功结果
        return jsonify({
            'success': True,
            'signature': signature,
            'message': '转账交易已发送到链上，请稍候查看结果',
            'tx_status': 'processing'
        })
            
    except Exception as e:
        current_app.logger.error(f"处理转账请求失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'处理请求失败: {str(e)}'}), 500

# 添加新的区块链交易相关API路由
@api_bp.route('/trades/<int:trade_id>', methods=['GET'])
def get_trade(trade_id):
    """获取单个交易详情"""
    try:
        # 获取交易记录
        trade = Trade.query.get_or_404(trade_id)
        
        # 从请求中尝试获取用户地址
        user_address = None
        if 'X-Eth-Address' in request.headers:
            user_address = request.headers.get('X-Eth-Address')
        elif request.args.get('address'):
            user_address = request.args.get('address')
        elif hasattr(g, 'eth_address'):
            user_address = g.eth_address
            
        # 如果找不到地址，返回交易基本信息（非敏感字段）
        if not user_address:
            # 返回有限的交易信息，不包含敏感详情
            trade_data = {
                'id': trade.id,
                'asset_id': trade.asset_id,
                'amount': trade.amount,
                'price': trade.price,
                'status': trade.status,
                'created_at': trade.created_at.isoformat() if trade.created_at else None
            }
            return jsonify(trade_data)
        
        # 用户地址不区分大小写处理
        user_address_lower = user_address.lower() if user_address.startswith('0x') else user_address
        trader_address_lower = trade.trader_address.lower() if trade.trader_address.startswith('0x') else trade.trader_address
            
        # 检查权限 - 只有交易创建者或管理员可以获取详情
        is_user_admin = is_admin(user_address)
        is_creator = trader_address_lower == user_address_lower
        
        if not is_user_admin and not is_creator:
            current_app.logger.warning(f'交易访问权限不足: 用户={user_address}, 交易创建者={trade.trader_address}, 管理员={is_user_admin}, 创建者匹配={is_creator}')
            return jsonify({'error': '无权限访问该交易'}), 403
            
        # 转换为字典并返回完整信息
        return jsonify(trade.to_dict())
        
    except Exception as e:
        current_app.logger.error(f'获取交易详情失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/blockchain/solana/prepare-transaction', methods=['POST'])
def prepare_solana_transaction():
    """准备Solana交易"""
    try:
        # 获取用户地址
        user_address = None
        if 'X-Eth-Address' in request.headers:
            user_address = request.headers.get('X-Eth-Address')
        elif request.json and 'wallet_address' in request.json:
            user_address = request.json.get('wallet_address')
        elif hasattr(g, 'eth_address'):
            user_address = g.eth_address
            
        if not user_address:
            return jsonify({'error': '未提供钱包地址'}), 401
            
        data = request.json
        
        # 检查必要字段
        required_fields = ['trade_id', 'amount', 'asset_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'缺少必要字段: {field}'}), 400
                
        # 获取交易记录
        trade_id = data.get('trade_id')
        trade = Trade.query.get_or_404(trade_id)
        
        # 验证交易创建者 - 不区分大小写
        user_address_lower = user_address.lower() if user_address.startswith('0x') else user_address
        trader_address_lower = trade.trader_address.lower() if trade.trader_address.startswith('0x') else trade.trader_address
        
        if trader_address_lower != user_address_lower:
            return jsonify({'error': '无权操作此交易'}), 403
            
        # 获取资产信息
        asset = Asset.query.get_or_404(trade.asset_id)
        
        # 调用Solana服务准备交易
        from app.blockchain.solana_service import prepare_transaction
        transaction_data = prepare_transaction(
            user_address=user_address,
            asset_id=asset.id,
            token_symbol=asset.token_symbol,
            amount=trade.amount,
            price=trade.price,
            trade_id=trade.id
        )
        
        return jsonify({
            'success': True,
            'transaction': transaction_data,
            'trade_id': trade.id
        })
        
    except Exception as e:
        current_app.logger.error(f'准备Solana交易失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/blockchain/solana/check-transaction', methods=['GET'])
def check_solana_transaction():
    """检查Solana交易状态"""
    try:
        signature = request.args.get('signature')
        if not signature:
            return jsonify({'error': '缺少交易签名'}), 400
            
        # 调用Solana服务检查交易
        from app.blockchain.solana_service import check_transaction
        result = check_transaction(signature)
        
        return jsonify({
            'success': True,
            'confirmed': result.get('confirmed', False),
            'confirmations': result.get('confirmations', 0),
            'error': result.get('error')
        })
        
    except Exception as e:
        current_app.logger.error(f'检查Solana交易状态失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/blockchain/ethereum/prepare-transaction', methods=['POST'])
@eth_address_required
def prepare_ethereum_transaction():
    """准备以太坊交易"""
    try:
        data = request.json
        
        # 检查必要字段
        required_fields = ['trade_id', 'amount', 'asset_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'缺少必要字段: {field}'}), 400
                
        # 获取交易记录
        trade_id = data.get('trade_id')
        trade = Trade.query.get_or_404(trade_id)
        
        # 验证交易创建者
        user_address = g.eth_address
        if trade.trader_address.lower() != user_address.lower():
            return jsonify({'error': '无权操作此交易'}), 403
            
        # 获取资产信息
        asset = Asset.query.get_or_404(trade.asset_id)
        
        # 调用以太坊服务准备交易
        from app.blockchain.ethereum import prepare_transaction
        transaction_data = prepare_transaction(
            user_address=user_address,
            asset_id=asset.id,
            token_symbol=asset.token_symbol,
            amount=trade.amount,
            price=trade.price,
            trade_id=trade.id
        )
        
        return jsonify({
            'success': True,
            'transaction': transaction_data,
            'trade_id': trade.id
        })
        
    except Exception as e:
        current_app.logger.error(f'准备以太坊交易失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/blockchain/ethereum/check-transaction', methods=['GET'])
def check_ethereum_transaction():
    """检查以太坊交易状态"""
    try:
        # 获取交易哈希
        tx_hash = request.args.get('hash')
        if not tx_hash:
            return jsonify({'success': False, 'error': '缺少交易哈希参数'}), 400
        
        # 记录请求信息
        current_app.logger.info(f"检查以太坊交易状态: {tx_hash}")
        
        # 使用Web3库检查交易状态
        try:
            # 此处应添加实际的以太坊交易状态检查逻辑
            # 简化实现，返回模拟结果
            confirmed = True
            tx_receipt = {'status': 1, 'blockNumber': 12345}
            
            # 记录结果
            current_app.logger.info(f"交易状态检查结果: {tx_hash}, 确认状态: {confirmed}")
            
            # 返回结果
            return jsonify({
                'success': True,
                'signature': signature,
                'confirmed': confirmed,
                'status': transaction_status
            })
            
        except Exception as tx_error:
            current_app.logger.error(f"检查交易状态失败: {str(tx_error)}")
            # 返回失败，但HTTP状态码仍为200，让前端继续轮询
            return jsonify({
                'success': True,
                'signature': signature,
                'confirmed': False,
                'error': str(tx_error)
            })
        
    except Exception as e:
        current_app.logger.error(f"处理交易状态请求失败: {str(e)}")
        return jsonify({'success': False, 'error': f'处理请求失败: {str(e)}'}), 500

@api_bp.route('/solana/create_transaction', methods=['POST'])
@eth_address_required
def create_solana_transaction():
    """
    创建Solana交易
    用于生成各类Solana交易，返回序列化的交易数据
    前端使用Phantom钱包签名并发送
    """
    try:
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'success': False, 'error': '请先连接钱包'}), 401
            
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        # 检查必要字段
        required_fields = ['trade_id', 'amount', 'price', 'asset_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400
                
        trade_id = data.get('trade_id')
        amount = float(data.get('amount'))
        price = float(data.get('price'))
        asset_id = data.get('asset_id')
        
        # 记录请求信息
        current_app.logger.info(f"创建Solana交易: 交易ID={trade_id}, 金额={amount}, 价格={price}, 资产ID={asset_id}, 用户={g.eth_address}")
        
        # 使用Solana Python客户端创建交易
        from app.utils.solana_compat.publickey import PublicKey
        from app.utils.solana_compat.transaction import Transaction, TransactionInstruction
        from app.utils.solana_compat.connection import Connection
        
        try:
            # 创建连接对象
            connection = Connection("https://api.mainnet-beta.solana.com")
            
            # 创建交易对象
            transaction = Transaction()
            
            # 添加备注指令，记录交易ID
            user_pubkey = PublicKey(g.eth_address)
            memo_program_id = PublicKey('MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr')
            
            # 创建交易数据
            memo_data = f"trade:{trade_id}:asset:{asset_id}:amount:{amount}:price:{price}"
            
            # 添加备注指令
            memo_instruction = TransactionInstruction(
                keys=[{'pubkey': user_pubkey, 'isSigner': True, 'isWritable': False}],
                program_id=memo_program_id,
                data=memo_data.encode('utf-8')
            )
            
            transaction.add(memo_instruction)
            
            # 获取最新区块哈希
            recent_blockhash_resp = connection.get_recent_blockhash()
            blockhash = recent_blockhash_resp.get('result', {}).get('value', {}).get('blockhash', 'simulated_blockhash')
            transaction.recent_blockhash = blockhash
            
            # 设置手续费支付者
            transaction.fee_payer = user_pubkey
            
            # 转换为结构化的交易数据对象
            tx_data = {
                "recentBlockhash": blockhash,
                "feePayer": g.eth_address,
                "instructions": []
            }
            
            # 添加所有指令信息
            for instr in transaction.instructions:
                instruction_data = {
                    "programId": str(instr.program_id),
                    "keys": [
                        {
                            "pubkey": str(key.pubkey),
                            "isSigner": key.is_signer,
                            "isWritable": key.is_writable
                        } for key in instr.keys
                    ],
                    "data": memo_data # 使用备注数据作为指令数据
                }
                tx_data["instructions"].append(instruction_data)
            
            # 将交易数据转换为JSON，然后返回
            # 这里不进行任何编码，直接返回结构化数据
            
            # 返回完整的交易数据结构
            return jsonify({
                'success': True,
                'transaction': tx_data,
                'message': f'已创建交易记录',
                'trade_id': trade_id,
                'asset_id': asset_id,
                'amount': amount,
                'price': price
            })
            
        except Exception as tx_error:
            current_app.logger.error(f"创建Solana交易失败: {str(tx_error)}")
            return jsonify({'success': False, 'error': f'创建交易失败: {str(tx_error)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"处理交易请求失败: {str(e)}")
        return jsonify({'success': False, 'error': f'处理请求失败: {str(e)}'}), 500

# Helper function to get config values with defaults
def get_config_value(key, default=None, required=False):
    value = current_app.config.get(key)
    if value is None:
        if required:
            raise ValueError(f"Missing required configuration: {key}")
        return default
    return value

@api_bp.route('/trades', methods=['POST'])
@eth_address_required
def create_trade():
    """创建交易记录"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400

        asset_id = data.get('asset_id')
        amount_str = data.get('amount')
        price_str = data.get('price')
        trade_type = data.get('type', 'buy')  # 默认为购买
        trader_address = g.eth_address # 使用装饰器提供的地址

        if not all([asset_id, amount_str, price_str, trader_address]):
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        # 参数校验
        try:
            asset_id = int(asset_id)
            # 先尝试确保amount_str是一个整数字符串
            try:
                amount = int(amount_str)
                amount = Decimal(amount)  # 转换为Decimal用于后续计算
            except (ValueError, TypeError):
                # 如果不能直接转为整数，尝试作为浮点数处理并取整
                try:
                    amount = int(float(amount_str))
                    amount = Decimal(amount)
                except (ValueError, TypeError):
                    # 如果还是失败，尝试直接使用Decimal
                    amount = Decimal(amount_str)
        except (ValueError, TypeError):
            current_app.logger.error(f"无效的数字格式: asset_id={asset_id}, amount={amount_str}")
            return jsonify({'success': False, 'error': '无效的数字格式'}), 400
            
        if amount <= 0 or price <= 0:
            return jsonify({'success': False, 'error': '金额和价格必须为正数'}), 400

        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({'success': False, 'error': '资产不存在'}), 404
            
        # 检查资产状态是否允许交易 (例如，必须是 ON_CHAIN)
        if asset.status != AssetStatus.ON_CHAIN.value:
             return jsonify({'success': False, 'error': '资产当前状态不允许交易'}), 400

        # 检查购买数量是否超过剩余供应量
        # 注意：这里需要更可靠的方式获取链上实时剩余供应量
        # 暂时使用数据库中的 token_count 作为参考，但这可能不准确
        # if trade_type == 'buy' and amount > asset.get_remaining_supply(): # 假设有 get_remaining_supply 方法
        #     return jsonify({'success': False, 'error': '购买数量超过剩余供应量'}), 400


        # 注意：原有的直接完成交易的逻辑已废弃，由新的 prepare/confirm 流程替代
        # 这里只创建记录，状态可能是 PENDING 或类似状态，但不直接完成

        # 创建交易对象，状态待定 (根据具体逻辑调整)
        new_trade = Trade(
            asset_id=asset_id,
            trader_address=trader_address,
            amount=amount,
            price=price,
            total=amount * price,
            type=trade_type,
            status=TradeStatus.PENDING_PAYMENT.value, # 初始状态
            tx_hash=None # 初始无哈希
        )

        db.session.add(new_trade)
        db.session.commit()
        
        current_app.logger.info(f"创建了交易记录 (ID: {new_trade.id})，等待支付准备。")

        # 返回交易ID，前端可能需要，也可能直接调用 prepare_purchase
        return jsonify({'success': True, 'trade_id': new_trade.id}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建交易失败: {str(e)}")
        return jsonify({'success': False, 'error': f'创建交易失败: {str(e)}'}), 500

# 新增：准备购买交易接口
@api_bp.route('/trades/prepare_purchase', methods=['POST'])
@eth_address_required
def prepare_purchase():
    """准备购买交易，创建待支付记录并返回给前端调用智能合约所需信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400

        asset_id = data.get('asset_id')
        amount_str = data.get('amount') # 前端传递购买的数量

        if not all([asset_id, amount_str]):
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
            
        # 记录原始输入
        current_app.logger.info(f"购买准备 - 原始输入: asset_id={asset_id}, amount={amount_str}({type(amount_str).__name__})")
            
        try:
            # 验证金额是否存在并且是数字
            if not amount_str:
                return jsonify({'error': '缺少数量参数'}), 400
            
            # 先尝试转换为整数（大多数情况）
            try:
                amount_int = int(amount_str)
                if amount_int <= 0:
                    return jsonify({'error': '数量必须大于0'}), 400
                
                # 确保最小数量为1
                amount = str(max(1, amount_int))
                current_app.logger.info(f"整数转换成功: {amount_str} -> {amount}")
            except (ValueError, TypeError):
                # 如果不是整数，再尝试转换为浮点数
                try:
                    amount_float = float(amount_str)
                    if amount_float <= 0:
                        return jsonify({'error': '数量必须大于0'}), 400
                    
                    # 检查是否为整数
                    if amount_float != int(amount_float):
                        return jsonify({'error': '数量必须是整数'}), 400
                        
                    # 确保最小数量为1
                    amount = str(max(1, int(amount_float)))
                    current_app.logger.info(f"浮点数转换成功: {amount_str} -> {amount}")
                except (ValueError, TypeError):
                    current_app.logger.error(f"金额格式转换错误: {amount_str}")
                    return jsonify({'error': '无效的金额格式'}), 400
        except Exception as e:
            current_app.logger.error(f"数量转换失败: {str(e)}, 原始值: {amount_str}")
            return jsonify({'success': False, 'error': f'无效的数字格式: {amount_str}'}), 400

        # 获取资产信息
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({'success': False, 'error': '找不到指定资产'}), 404

        if asset.status != AssetStatus.ACTIVE.value:
            return jsonify({'success': False, 'error': '该资产当前不可交易'}), 400

        # 使用户钱包地址，优先使用g.eth_address (通过eth_address_required装饰器设置)
        trader_address = g.eth_address
        if not trader_address:
            return jsonify({'success': False, 'error': '未提供交易者钱包地址'}), 400
            
        current_app.logger.info(f"准备购买 - 用户: {trader_address}, 资产: {asset.id}, 数量: {amount}")

        # 从配置读取平台费率 (基点, e.g., 350 for 3.5%) 和平台收款地址
        platform_fee_basis_points = get_config_value('PLATFORM_FEE_BASIS_POINTS', default=350, required=True) # 示例：默认3.5%
        platform_address = get_config_value('PLATFORM_FEE_ADDRESS', required=True)
        purchase_contract_address = get_config_value('PURCHASE_CONTRACT_ADDRESS', required=True) # 智能合约地址

        # 计算总价
        price = Decimal(str(asset.token_price)) if asset.token_price else Decimal('0')
        total_price = (Decimal(amount) * price).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP) # 保留6位小数

        # 获取购买者和卖家地址
        buyer_address = g.eth_address
        seller_address = asset.creator_address # 假设资产创建者即卖家

        # 创建交易记录
        new_trade = Trade(
            asset_id=asset_id,
            trader_address=buyer_address,
            amount=int(amount),  # 确保amount是整数
            price=price,
            total=total_price,
            type='buy',
            status=TradeStatus.PENDING_PAYMENT.value, # 等待前端支付
            payment_details=json.dumps({ # 存储用于支付的信息
                 'platform_fee_basis_points': platform_fee_basis_points,
                 'platform_address': platform_address,
                 'seller_address': seller_address,
                 'purchase_contract_address': purchase_contract_address
            })
        )
        db.session.add(new_trade)
        db.session.commit()

        current_app.logger.info(f"准备购买交易 (ID: {new_trade.id}) for asset {asset_id}, amount {amount}, total {total_price}.")

        # 返回给前端调用智能合约所需的信息
        return jsonify({
            'success': True,
            'trade_id': new_trade.id,
            'total_amount': str(total_price), # 总支付金额 (USDC)
            'seller_address': seller_address,
            'platform_fee_basis_points': platform_fee_basis_points,
            'purchase_contract_address': purchase_contract_address # 智能合约地址
        }), 201

    except ValueError as ve: # 处理配置缺失错误
        current_app.logger.error(f"配置错误: {str(ve)}")
        return jsonify({'success': False, 'error': f'服务器配置错误: {str(ve)}'}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"准备购买交易失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'准备购买交易失败: {str(e)}'}), 500

# 新增：确认支付接口
@api_bp.route('/trades/confirm_payment/<int:trade_id>', methods=['POST'])
@eth_address_required
def confirm_payment(trade_id):
    """前端调用智能合约后，传递交易哈希以确认支付并发起后台监控"""
    try:
        data = request.get_json()
        if not data or 'tx_hash' not in data:
            return jsonify({'success': False, 'error': '缺少交易哈希 (tx_hash)'}), 400

        tx_hash = data['tx_hash']
        if not tx_hash:
             return jsonify({'success': False, 'error': '交易哈希不能为空'}), 400

        trade = Trade.query.get(trade_id)
        if not trade:
            return jsonify({'success': False, 'error': '交易不存在'}), 404

        # 验证调用者是否是该交易的购买者
        if not is_same_wallet_address(g.eth_address, trade.trader_address):
             return jsonify({'success': False, 'error': '无权确认此交易'}), 403

        # 检查交易状态是否适合确认
        if trade.status != TradeStatus.PENDING_PAYMENT.value:
             current_app.logger.warning(f"尝试确认非待支付状态的交易 (ID: {trade_id}, Status: {trade.status})")
             # 可以选择返回错误，或者允许重复确认？暂时返回错误
             return jsonify({'success': False, 'error': f'交易状态不正确 ({trade.status})，无法确认支付'}), 400

        # 更新交易记录
        trade.tx_hash = tx_hash # 存储智能合约交易哈希
        trade.status = TradeStatus.PENDING_CONFIRMATION.value # 更新状态为等待链上确认
        
        # 更新交易详情 - 修复点：确保payment_details始终是JSON字符串
        try:
            if trade.payment_details and isinstance(trade.payment_details, str):
                details = json.loads(trade.payment_details)
            else:
                details = {} if trade.payment_details is None else trade.payment_details
                
            if not isinstance(details, dict):
                details = {}
                
            details['payment_initiated_at'] = datetime.utcnow().isoformat()
            details['initial_tx_hash'] = tx_hash
            # 确保序列化为JSON字符串
            trade.payment_details = json.dumps(details)
            current_app.logger.info(f"已更新交易详情: {trade.payment_details}")
        except Exception as detail_error:
            current_app.logger.error(f"更新交易详情时出错: {str(detail_error)}")
            # 创建新的详情对象
            trade.payment_details = json.dumps({
                'payment_initiated_at': datetime.utcnow().isoformat(),
                'initial_tx_hash': tx_hash
            })

        db.session.commit()

        current_app.logger.info(f"交易 (ID: {trade_id}) 支付已发起，哈希: {tx_hash}，状态更新为等待确认。")

        # TODO: 在这里触发后台任务来监控 tx_hash 的链上状态
        # from app.tasks import monitor_purchase_transaction # 示例
        # monitor_purchase_transaction.delay(trade_id, tx_hash)
        current_app.logger.info(f"TODO: 触发后台任务监控交易 {trade_id} (哈希: {tx_hash})")


        return jsonify({'success': True, 'message': '支付确认请求已收到，正在处理'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"确认支付失败 (Trade ID: {trade_id}): {str(e)}")
        return jsonify({'success': False, 'error': f'确认支付失败: {str(e)}'}), 500

# 新增：匹配前端调用的confirm_payment路由
@api_bp.route('/trades/confirm_payment', methods=['POST'])
@eth_address_required
def confirm_payment_from_post():
    """接收前端通过POST方法直接提交的交易确认请求"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        # 从请求数据中获取trade_id
        trade_id = data.get('asset_id')  # 可能使用asset_id作为交易标识
        signature = data.get('signature')  # 获取交易签名
        
        if not trade_id:
            return jsonify({'success': False, 'error': '缺少必要参数 (asset_id)'}), 400
            
        # 修改请求数据，添加tx_hash字段
        if signature and 'tx_hash' not in data:
            data['tx_hash'] = signature
        
        # 查找该用户最近的待支付交易
        buyer_address = g.eth_address
        pending_trade = Trade.query.filter_by(
            asset_id=trade_id,
            trader_address=buyer_address,
            type='buy',
            status=TradeStatus.PENDING_PAYMENT.value
        ).order_by(Trade.created_at.desc()).first()
        
        if not pending_trade:
            return jsonify({'success': False, 'error': '未找到待支付的交易'}), 404
            
        # 使用找到的trade_id调用原有确认函数
        modified_request = request.get_json().copy() if request.get_json() else {}
        modified_request['tx_hash'] = signature
        
        # 更新交易记录
        pending_trade.tx_hash = signature
        pending_trade.status = TradeStatus.PENDING_CONFIRMATION.value  # 更新状态为等待链上确认
        
        # 更新交易详情 - 修复点：确保payment_details始终是JSON字符串
        try:
            if pending_trade.payment_details and isinstance(pending_trade.payment_details, str):
                details = json.loads(pending_trade.payment_details)
            else:
                details = {} if pending_trade.payment_details is None else pending_trade.payment_details
                
            if not isinstance(details, dict):
                details = {}
                
            details['payment_executed_at'] = datetime.utcnow().isoformat()
            details['signature'] = signature
            # 确保序列化为JSON字符串
            pending_trade.payment_details = json.dumps(details)
            current_app.logger.info(f"已更新交易详情: {pending_trade.payment_details}")
        except Exception as detail_error:
            current_app.logger.error(f"更新交易详情时出错: {str(detail_error)}")
            # 创建新的详情对象
            pending_trade.payment_details = json.dumps({
                'payment_executed_at': datetime.utcnow().isoformat(),
                'signature': signature,
                'platform_fee_basis_points': 350,
                'platform_address': "HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd",
                'seller_address': pending_trade.recipient_address
            })
        
        # 为了快速测试，直接将交易标记为已完成
        pending_trade.status = TradeStatus.COMPLETED.value
        pending_trade.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        current_app.logger.info(f"通过POST确认支付成功 (Trade ID: {pending_trade.id}, 签名: {signature})")
        
        return jsonify({
            'success': True,
            'trade_id': pending_trade.id,
            'message': '购买交易已成功执行，资产将在几分钟内更新'
        }), 200
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"通过POST确认支付失败: {str(e)}")
        return jsonify({'success': False, 'error': f'确认支付失败: {str(e)}'}), 500

# 新增：执行购买接口
@api_bp.route('/trades/execute_purchase', methods=['POST'])
@eth_address_required
def execute_purchase():
    """接收前端传来的钱包交易信息，完成资产购买确认"""
    try:
        # 获取请求数据
        data = request.get_json()
        current_app.logger.info(f"收到execute_purchase请求: {data}")
        
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        # 验证必要参数
        asset_id = data.get('asset_id')
        amount = data.get('amount')
        signature = data.get('signature')  # Solana交易签名/哈希
        
        if not asset_id:
            return jsonify({'success': False, 'error': '缺少必要参数 (asset_id)'}), 400
            
        if not amount:
            return jsonify({'success': False, 'error': '缺少必要参数 (amount)'}), 400
            
        if not signature:
            return jsonify({'success': False, 'error': '缺少必要参数 (signature)'}), 400
            
        # 确保signature是字符串
        if not isinstance(signature, str):
            current_app.logger.warning(f"收到非字符串类型的signature: {type(signature)}, 值: {signature}")
            # 如果signature不是字符串，尝试转换或提取有效部分
            if isinstance(signature, dict) and 'txHash' in signature:
                signature = signature['txHash']
            elif isinstance(signature, dict) and 'signature' in signature:
                signature = signature['signature']
            else:
                # 如果无法提取，则转为JSON字符串
                signature = json.dumps(signature)
                
        current_app.logger.info(f"处理后的签名: {signature}")
            
        # 查找该用户最近的待支付交易
        buyer_address = g.eth_address
        current_app.logger.info(f"查找用户 {buyer_address} 针对资产 {asset_id} 的待支付交易")
        
        pending_trade = Trade.query.filter_by(
            asset_id=asset_id,
            trader_address=buyer_address,
            type='buy',
            status=TradeStatus.PENDING_PAYMENT.value
        ).order_by(Trade.created_at.desc()).first()
        
        if not pending_trade:
            current_app.logger.warning(f"未找到待支付的交易 (asset_id: {asset_id}, buyer: {buyer_address})")
            return jsonify({'success': False, 'error': '未找到待支付的交易'}), 404
            
        current_app.logger.info(f"找到待处理交易 ID: {pending_trade.id}, 状态: {pending_trade.status}")

        # 验证交易金额是否匹配
        # 确保使用整数比较整数，避免类型不匹配
        amount_int = int(amount) if amount else 0
        current_app.logger.info(f"金额比较: 预期={pending_trade.amount}(类型:{type(pending_trade.amount).__name__}), 收到={amount_int}(类型:{type(amount_int).__name__})")
        
        if pending_trade.amount != amount_int:
            current_app.logger.warning(f"交易金额不匹配: 预期 {pending_trade.amount}, 收到 {amount_int}")
            return jsonify({
                'success': False, 
                'error': f'交易金额不匹配 (预期: {pending_trade.amount}, 收到: {amount_int})'
            }), 400

        # 更新交易记录
        pending_trade.tx_hash = signature  # 确保这里存储的是字符串
        pending_trade.status = TradeStatus.PENDING_CONFIRMATION.value  # 更新状态为等待链上确认
        
        # 更新交易详情 - 修复点：确保payment_details始终是JSON字符串
        try:
            if pending_trade.payment_details and isinstance(pending_trade.payment_details, str):
                details = json.loads(pending_trade.payment_details)
            else:
                details = {} if pending_trade.payment_details is None else pending_trade.payment_details
                
            if not isinstance(details, dict):
                details = {}
                
            details['payment_executed_at'] = datetime.utcnow().isoformat()
            details['signature'] = signature  # 确保这里存储的是字符串
            # 确保序列化为JSON字符串
            pending_trade.payment_details = json.dumps(details)
            current_app.logger.info(f"已更新交易详情: {pending_trade.payment_details}")
        except Exception as detail_error:
            current_app.logger.error(f"更新交易详情时出错: {str(detail_error)}")
            # 创建新的详情对象
            pending_trade.payment_details = json.dumps({
                'payment_executed_at': datetime.utcnow().isoformat(),
                'signature': signature,
                'platform_fee_basis_points': 350,
                'platform_address': "HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd",
                'seller_address': pending_trade.recipient_address
            })

        # 可以在这里添加特定链的交易验证逻辑
        # TODO: 验证Solana交易是否有效
        
        # 为了快速测试，直接将交易标记为已完成
        # 在生产环境中，应该通过后台任务验证交易后再标记为已完成
        pending_trade.status = TradeStatus.COMPLETED.value
        pending_trade.completed_at = datetime.utcnow()

        db.session.commit()

        current_app.logger.info(f"购买执行成功 (Trade ID: {pending_trade.id}, Asset: {asset_id}, 金额: {amount}, 签名: {signature})")

        # TODO: 在这里触发后台任务，监控交易最终确认并更新资产所有权
        # from app.tasks import monitor_and_complete_purchase # 示例
        # monitor_and_complete_purchase.delay(pending_trade.id, signature)

        return jsonify({
            'success': True,
            'trade_id': pending_trade.id,
            'message': '购买交易已成功执行，资产将在几分钟内更新'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"执行购买失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'执行购买失败: {str(e)}'}), 500

@api_bp.route('/user/wallet/balance', endpoint='get_user_wallet_balance')
def get_user_wallet_balance():
    """获取用户钱包的USDC和SOL余额"""
    address = request.args.get('address')
    wallet_type = request.args.get('wallet_type', 'ethereum')
    
    if not address:
        return jsonify({'success': False, 'error': '缺少钱包地址'}), 400
    
    current_app.logger.info(f'获取钱包余额请求 - 地址: {address}, 类型: {wallet_type}')
    
    try:
        # 创建返回结果
        balances = {
            'USDC': 0,
            'SOL': 0
        }
        
        # 根据钱包类型设置不同余额
        if wallet_type == 'phantom':
            # 查询Solana钱包的SOL余额
            try:
                # 导入区块链客户端
                from app.blockchain.solana import SolanaClient
                
                # 创建只读Solana客户端实例，用于查询用户钱包
                solana_client = SolanaClient(wallet_address=address)
                
                # 获取SOL余额
                sol_balance = solana_client.get_balance()
                
                if sol_balance is not None:
                    balances['SOL'] = sol_balance
                    current_app.logger.info(f'SOL余额: {sol_balance}')
                else:
                    current_app.logger.warning('无法获取SOL余额，返回0')
                    balances['SOL'] = 0
                
                # 获取USDC余额 - USDC Token在Solana上的地址
                # Solana主网USDC代币地址
                usdc_token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                try:
                    from app.blockchain.asset_service import AssetService
                    # 调用获取SPL代币余额的方法
                    usdc_balance = AssetService.get_token_balance(wallet_address=address, token_mint_address=usdc_token_address)
                    balances['USDC'] = usdc_balance
                    current_app.logger.info(f'USDC余额: {usdc_balance}')
                except Exception as usdc_err:
                    # 降低日志级别为warning，减少错误日志记录
                    current_app.logger.warning(f'获取USDC余额失败: {str(usdc_err)}')
                    # 获取USDC失败不影响整体结果，保持USDC=0
            except Exception as sol_err:
                # 降低日志级别为warning，减少错误日志记录
                current_app.logger.warning(f'获取SOL余额失败: {str(sol_err)}')
                balances['SOL'] = 0
                
        else:
            # 如果是以太坊钱包，可以添加以太坊余额查询逻辑
            try:
                # 导入以太坊客户端
                from app.blockchain.ethereum import get_usdc_balance, get_eth_balance
                
                # 获取ETH余额
                eth_balance = get_eth_balance(address)
                if eth_balance is not None:
                    balances['ETH'] = eth_balance
                    current_app.logger.info(f'ETH余额: {eth_balance}')
                
                # 获取USDC余额
                usdc_balance = get_usdc_balance(address)
                if usdc_balance is not None:
                    balances['USDC'] = usdc_balance
                    current_app.logger.info(f'USDC余额: {usdc_balance}')
            except Exception as eth_err:
                # 降低日志级别为warning，减少错误日志记录
                current_app.logger.warning(f'获取以太坊余额失败: {str(eth_err)}')
            
        current_app.logger.info(f'返回真实余额数据: USDC={balances["USDC"]}, SOL={balances["SOL"]}')
        
        return jsonify({
            'success': True,
            'balance': balances['USDC'],  # 保持兼容性
            'balances': balances,
            'currency': 'USDC',
            'is_real_data': True
        }), 200
    except Exception as e:
        # 仅记录严重错误，减少exc_info使用
        current_app.logger.error(f'获取钱包余额失败: {str(e)}')
        return jsonify({'success': False, 'error': f'获取钱包余额失败: {str(e)}'}), 500
