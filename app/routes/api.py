from flask import jsonify, request, g, current_app, session
from app.models.user import User
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.trade import Trade
from app import db
from app.utils.decorators import token_required, eth_address_required
from .admin import is_admin, get_admin_permissions
import os
import json
from werkzeug.utils import secure_filename
from flask import Blueprint
import random
from app.models.dividend import DividendRecord
from functools import wraps
from datetime import datetime, timedelta

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
    # 将所有地址转换为小写进行比较
    admin_addresses = {addr.lower(): config for addr, config in admin_config.items()}
    is_admin = address.lower() in admin_addresses
    current_app.logger.info(f'检查结果: {is_admin}')
    return is_admin

# 缓存装饰器
def cache_permission(timeout=300):  # 默认缓存5分钟
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapped
    return decorator

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
    """获取资产详情"""
    try:
        current_app.logger.info(f'正在获取资产详情，ID: {asset_id}')
        asset = Asset.query.get(asset_id)
        
        if not asset:
            current_app.logger.error(f'资产不存在，ID: {asset_id}')
            return jsonify({'error': '资产不存在'}), 404
            
        # 如果资产已审核通过，直接允许访问
        if asset.status == AssetStatus.APPROVED:
            asset_dict = asset.to_dict()
            # 如果是类不动产，移除面积字段
            if asset.asset_type == AssetType.SEMI_REAL_ESTATE:
                asset_dict.pop('area', None)
            return jsonify(asset_dict), 200
            
        # 从请求头、URL参数或cookie获取地址
        eth_address = request.headers.get('X-Eth-Address') or \
                     request.args.get('eth_address') or \
                     request.cookies.get('eth_address')
        
        # 如果未提供钱包地址，返回基本信息
        if not eth_address:
            asset_dict = {
                'id': asset.id,
                'name': asset.name,
                'asset_type': asset.asset_type.value,
                'status': asset.status.value
            }
            return jsonify(asset_dict), 200
        
        # 检查是否是管理员或资产所有者
        is_admin = is_admin_address(eth_address)
        is_owner = eth_address.lower() == asset.owner_address.lower()
        
        # 如果是管理员或所有者，返回完整信息
        if is_admin or is_owner:
            asset_dict = asset.to_dict()
            # 如果是类不动产，移除面积字段
            if asset.asset_type == AssetType.SEMI_REAL_ESTATE:
                asset_dict.pop('area', None)
            return jsonify(asset_dict), 200
            
        # 其他情况返回基本信息
        asset_dict = {
            'id': asset.id,
            'name': asset.name,
            'asset_type': asset.asset_type.value,
            'status': asset.status.value
        }
        return jsonify(asset_dict), 200
        
    except Exception as e:
        current_app.logger.error(f'获取资产详情失败: {str(e)}', exc_info=True)
        return jsonify({'error': '获取资产详情失败'}), 500

@api_bp.route('/assets/create', methods=['POST'])
@eth_address_required
def create_asset():
    """创建资产"""
    try:
        eth_address = g.eth_address
        if not eth_address:
            current_app.logger.warning('创建资产时未提供钱包地址')
            return jsonify({'error': '请先连接钱包'}), 401

        # 验证必填字段
        required_fields = ['name', 'type', 'location', 'description', 'total_value', 'token_price', 'annual_revenue']
        for field in required_fields:
            if not request.form.get(field):
                return jsonify({'error': f'请填写{field}字段'}), 400

        # 验证资产类型
        asset_type = request.form.get('type')
        if asset_type not in ['10', '20']:
            return jsonify({'error': '无效的资产类型'}), 400

        # 验证面积（仅对不动产）
        if asset_type == '10' and not request.form.get('area'):
            return jsonify({'error': '请填写建筑面积'}), 400

        # 验证图片
        if 'images' not in request.files:
            return jsonify({'error': '请至少上传一张资产图片'}), 400

        # 验证文档
        if 'documents' not in request.files:
            return jsonify({'error': '请上传必要的资产文档'}), 400

        # 创建资产记录
        asset = Asset(
            name=request.form.get('name'),
            asset_type=int(asset_type),
            location=request.form.get('location'),
            description=request.form.get('description'),
            area=float(request.form.get('area', 0)),
            total_value=float(request.form.get('total_value')),
            token_price=float(request.form.get('token_price')),
            annual_revenue=float(request.form.get('annual_revenue')),
            owner_address=eth_address,
            creator_address=eth_address,
            status=AssetStatus.PENDING.value
        )

        # 保存到数据库
        db.session.add(asset)
        db.session.commit()

        # 处理文件上传
        try:
            asset_type_folder = 'real_estate' if asset_type == '10' else 'quasi_real_estate'
            
            # 处理图片
            images = request.files.getlist('images')
            image_paths = []
            for image in images:
                if image and image.filename and allowed_file(image.filename, ['jpg', 'jpeg', 'png', 'gif']):
                    try:
                        # 构建文件名
                        ext = image.filename.rsplit(".", 1)[1].lower()
                        filename = f'{asset_type_folder}/{asset.id}/images/image_{len(image_paths)+1}.{ext}'
                        
                        # 读取文件内容
                        file_data = image.read()
                        
                        # 上传到七牛云
                        storage = current_app.extensions.get('storage')
                        if storage is None:
                            raise Exception("七牛云存储未初始化")
                            
                        url = storage.upload(file_data, filename)
                        if url:
                            image_paths.append(url)
                            current_app.logger.info(f'上传图片成功: {url}')
                        else:
                            raise Exception("七牛云上传失败")
                            
                    except Exception as e:
                        current_app.logger.error(f'上传图片失败: {str(e)}')
                        continue
            
            if image_paths:
                asset.images = json.dumps(image_paths)
            
            # 处理文档
            documents = request.files.getlist('documents')
            doc_paths = []
            for doc in documents:
                if doc and doc.filename and allowed_file(doc.filename, ['pdf', 'doc', 'docx']):
                    try:
                        # 构建文件名
                        ext = doc.filename.rsplit(".", 1)[1].lower()
                        filename = f'{asset_type_folder}/{asset.id}/documents/document_{len(doc_paths)+1}.{ext}'
                        
                        # 读取文件内容
                        file_data = doc.read()
                        
                        # 上传到七牛云
                        storage = current_app.extensions.get('storage')
                        if storage is None:
                            raise Exception("七牛云存储未初始化")
                            
                        url = storage.upload(file_data, filename)
                        if url:
                            doc_paths.append(url)
                            current_app.logger.info(f'上传文档成功: {url}')
                        else:
                            raise Exception("七牛云上传失败")
                            
                    except Exception as e:
                        current_app.logger.error(f'上传文档失败: {str(e)}')
                        continue
            
            if doc_paths:
                asset.documents = json.dumps(doc_paths)
            
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f'文件上传失败: {str(e)}')
            db.session.delete(asset)
            db.session.commit()
            return jsonify({'error': '文件上传失败'}), 500

        return jsonify({
            'message': '资产创建成功',
            'id': asset.id
        }), 201

    except Exception as e:
        current_app.logger.error(f'创建资产失败: {str(e)}')
        return jsonify({'error': '创建资产失败'}), 500

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
        asset.total_value = float(request.form.get('total_value'))
        asset.annual_revenue = float(request.form.get('annual_revenue'))
        asset.token_price = float(request.form.get('token_price'))
        asset.token_supply = int(request.form.get('token_supply'))
        asset.token_symbol = request.form.get('token_symbol')
        
        # 处理图片和文档
        if 'images' in request.files:
            images = request.files.getlist('images')
            if images and any(image.filename for image in images):
                asset.images = save_files(images, asset.asset_type.value.lower(), asset_id)
                
        if 'documents' in request.files:
            documents = request.files.getlist('documents')
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
def list_trades():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    asset_id = request.args.get('asset_id', type=int)
    
    query = Trade.query
    if asset_id:
        query = query.filter_by(asset_id=asset_id)
        
    pagination = query.order_by(Trade.created_at.desc()).paginate(
        page=page, per_page=per_page)
    trades = [trade.to_dict() for trade in pagination.items]
    
    return jsonify({
        'trades': trades,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200

@api_bp.route('/trades', methods=['POST'])
@eth_address_required
def create_trade():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请提供交易信息'}), 400
        
    required_fields = ['asset_id', 'amount', 'trade_type']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '请填写所有必要字段'}), 400
        
    asset = Asset.query.get_or_404(data['asset_id'])
    if asset.status != AssetStatus.APPROVED:
        return jsonify({'error': '资产未获批准'}), 400
        
    # 验证交易类型
    if data['trade_type'] not in ['buy', 'sell']:
        return jsonify({'error': '无效的交易类型'}), 400
        
    # 验证交易数量
    amount = int(data['amount'])
    if amount <= 0:
        return jsonify({'error': '交易数量必须大于0'}), 400

    # 检查是否是自交易
    is_self_trade = data.get('is_self_trade', False)
    
    # 如果不是自交易，需要验证代币余额等
    if not is_self_trade:
        # TODO: 这里可以添加代币余额验证等逻辑
        pass

    try:
        # 创建交易记录
        trade = Trade(
            asset_id=asset.id,
            type=data['trade_type'],
            amount=amount,
            price=0 if is_self_trade else asset.token_price,  # 自交易价格为0
            trader_address=g.eth_address,
            is_self_trade=is_self_trade
        )
        
        db.session.add(trade)
        db.session.commit()
        
        return jsonify(trade.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 

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

@api_bp.route("/<int:asset_id>/dividend_stats", methods=['GET'])
def get_dividend_stats(asset_id):
    """获取资产分红统计信息"""
    try:
        # 检查资产是否存在
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({'error': '资产不存在'}), 404

        # TODO: 从区块链获取实际的分红统计数据
        data = {
            'count': 0,  # 分红次数
            'total_amount': 0,  # 累计分红金额
            'holder_count': 0  # 当前持有人数
        }

        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f'获取分红统计失败: {str(e)}')
        return jsonify({'error': '获取分红统计失败'}), 500

@api_bp.route("/<int:asset_id>/dividend_history", methods=['GET'])
def get_dividend_history(asset_id):
    """获取资产分红历史记录"""
    try:
        # 检查资产是否存在
        asset = Asset.query.get(asset_id)
        if not asset:
            return jsonify({'error': '资产不存在'}), 404

        # TODO: 从区块链获取实际的分红历史数据
        data = {
            'records': [],  # 分红历史记录
            'total_amount': 0  # 累计分红金额
        }

        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f'获取分红历史失败: {str(e)}')
        return jsonify({'error': '获取分红历史失败'}), 500 

# 优化管理员检查API
@api_bp.route('/admin/check')
@cache_permission(timeout=300)
def check_admin():
    """检查管理员权限"""
    try:
        eth_address = request.headers.get('X-Eth-Address')
        if not eth_address:
            return jsonify({
                'is_admin': False,
                'permissions': [],
                'message': '未提供钱包地址'
            }), 200

        # 获取管理员权限信息
        admin_info = get_admin_permissions(eth_address)
        
        if not admin_info:
            return jsonify({
                'is_admin': False,
                'permissions': [],
                'message': '非管理员账户'
            }), 200

        return jsonify({
            'is_admin': True,
            'permissions': admin_info.get('permissions', []),
            'role': admin_info.get('role', ''),
            'message': '验证成功'
        }), 200

    except Exception as e:
        current_app.logger.error(f'检查管理员权限失败: {str(e)}')
        return jsonify({
            'is_admin': False,
            'permissions': [],
            'message': f'检查管理员权限失败: {str(e)}'
        }), 500

@api_bp.route('/assets/<int:asset_id>/check_permission', methods=['GET'])
@eth_address_required
def check_asset_permission(asset_id):
    """检查资产权限"""
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
        }), 200 

@api_bp.route('/assets/<int:asset_id>/holders', methods=['GET'])
def get_asset_holders(asset_id):
    """获取资产持有人信息"""
    try:
        # 检查资产是否存在
        asset = Asset.query.get_or_404(asset_id)
        
        # 检查请求者是否是资产所有者
        eth_address = request.headers.get('X-Eth-Address')
        if not eth_address or eth_address.lower() != asset.owner.lower():
            return jsonify({'error': '无权访问'}), 403
            
        # 模拟返回持有人数据
        return jsonify({
            'holders_count': 100,  # 模拟数据
            'total_supply': asset.token_supply
        })
        
    except Exception as e:
        current_app.logger.error(f'获取资产持有人信息失败: {str(e)}')
        return jsonify({'error': '获取持有人信息失败'}), 500

@api_bp.route('/assets/<int:asset_id>/dividend', methods=['POST'])
def create_dividend(asset_id):
    """创建分红记录"""
    try:
        # 检查资产是否存在
        asset = Asset.query.get_or_404(asset_id)
        
        # 检查请求者是否是资产所有者
        eth_address = request.headers.get('X-Eth-Address')
        if not eth_address or eth_address.lower() != asset.owner.lower():
            return jsonify({'error': '无权访问'}), 403
            
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
            
        total_amount = float(data.get('total_amount', 0))
        if total_amount <= 0:
            return jsonify({'error': '分红金额必须大于0'}), 400
            
        # 计算平台手续费(1%)和实际分红金额
        platform_fee = round(total_amount * 0.01, 2)
        actual_amount = total_amount - platform_fee
        
        # 创建分红记录
        dividend = DividendRecord(
            asset_id=asset_id,
            total_amount=total_amount,
            actual_amount=actual_amount,
            platform_fee=platform_fee,
            holders_count=data.get('holders_count', 0),
            gas_used=data.get('gas_used'),
            tx_hash=data.get('tx_hash', '')
        )
        
        db.session.add(dividend)
        db.session.commit()
        
        return jsonify(dividend.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'创建分红记录失败: {str(e)}')
        return jsonify({'error': '创建分红记录失败'}), 500

@api_bp.route('/assets/<int:asset_id>/dividend_history', methods=['GET'])
def get_asset_dividend_history(asset_id):
    """获取资产分红历史"""
    try:
        # 检查资产是否存在
        asset = Asset.query.get_or_404(asset_id)
        
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # 查询分红记录
        pagination = DividendRecord.query.filter_by(asset_id=asset_id)\
            .order_by(DividendRecord.created_at.desc())\
            .paginate(page=page, per_page=per_page)
            
        records = [record.to_dict() for record in pagination.items]
        
        return jsonify({
            'records': records,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page
        })
        
    except Exception as e:
        current_app.logger.error(f'获取分红历史失败: {str(e)}')
        return jsonify({'error': '获取分红历史失败'}), 500 

@api_bp.route('/user/preferences/language', methods=['POST'])
def update_language_preference():
    try:
        data = request.json
        language = data.get('language')
        
        if not language or language not in ['en', 'zh_Hant']:
            return jsonify({'error': 'Invalid language'}), 400
        
        # 语言偏好功能已移除，直接返回成功
        return jsonify({'message': 'Language preference updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 
