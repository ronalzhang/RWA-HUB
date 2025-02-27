from flask import jsonify, request, g, current_app, session
from app.models.user import User
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.trade import Trade
from app import db
from app.utils.decorators import token_required, eth_address_required
from .admin import is_admin
import os
import json
from werkzeug.utils import secure_filename
from flask import Blueprint
import random
from app.models.dividend import DividendRecord
from app.utils.storage import storage, upload_file
from app.config import Config as CONFIG
import time
import re
from sqlalchemy.exc import OperationalError

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
        # 检查钱包连接状态
        if not g.eth_address:
            return jsonify({'error': '请先连接钱包'}), 401
            
        # 获取表单数据
        data = request.form.to_dict()
        
        # 验证必填字段
        required_fields = ['name', 'type', 'location', 'token_symbol']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'缺少必填字段: {field}'}), 400
                
        # 验证代币符号
        token_symbol = data.get('token_symbol', '').strip().upper()
        if not token_symbol:
            return jsonify({'error': '代币符号不能为空'}), 400
            
        if not re.match(r'^RH-(?:10|20)\d{4}$', token_symbol):
            return jsonify({'error': '代币符号格式无效，必须为 RH-10YYYY 或 RH-20YYYY 格式，其中 YYYY 为4位数字'}), 400
            
        # 检查代币符号是否已存在
        existing_asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if existing_asset:
            return jsonify({'error': '代币符号已被使用'}), 400
                
        def safe_float(value, field_name):
            try:
                # 如果是None或空字符串，则报错
                if value is None or (isinstance(value, str) and not value.strip()):
                    raise ValueError(f"{field_name} 不能为空")
                    
                # 转换为float
                float_value = float(value)
                if float_value <= 0:
                    raise ValueError(f"{field_name} 必须大于0")
                return float_value
            except (ValueError, TypeError) as e:
                raise ValueError(f"{field_name} 无效: {str(e)}")
                
        def safe_int(value, field_name):
            try:
                # 如果是None或空字符串，则报错
                if value is None or (isinstance(value, str) and not value.strip()):
                    raise ValueError(f"{field_name} 不能为空")
                    
                # 转换为int
                int_value = int(float(value))  # 先转float再转int，以支持字符串形式的小数
                if int_value <= 0:
                    raise ValueError(f"{field_name} 必须大于0")
                return int_value
            except (ValueError, TypeError) as e:
                raise ValueError(f"{field_name} 无效: {str(e)}")
        
        # 获取资产类型
        asset_type = int(data.get('type', '10'))
        
        # 获取并验证total_value
        total_value = safe_float(data.get('total_value'), '总价值')
        
        # 验证面积（仅对不动产类型）
        area = None
        if asset_type == 10:  # 不动产类型
            area = safe_float(data.get('area'), '面积')
            
        # 创建资产记录
        asset = Asset(
            name=data.get('name'),
            description=data.get('description'),
            asset_type=asset_type,
            location=data.get('location'),
            area=area,
            total_value=total_value,
            token_symbol=token_symbol,
            token_price=safe_float(data.get('token_price'), '代币价格'),
            token_supply=safe_int(data.get('token_supply'), '代币数量'),
            annual_revenue=safe_float(data.get('annual_revenue'), '年收益'),
            status=AssetStatus.PENDING.value,
            owner_address=g.eth_address,
            creator_address=g.eth_address
        )
        
        db.session.add(asset)
        db.session.commit()
        current_app.logger.info(f'资产基本信息创建成功，ID: {asset.id}')
        
        # 处理图片上传
        image_paths = []
        if 'images[]' in request.form:
            image_paths = request.form.getlist('images[]')
            current_app.logger.info(f'收到 {len(image_paths)} 个图片URL')
            # 确保图片路径是有效的
            image_paths = [path for path in image_paths if path and isinstance(path, str)]
            current_app.logger.info(f'有效的图片路径: {image_paths}')

        # 处理文档上传
        document_paths = []
        if 'documents[]' in request.form:
            document_paths = request.form.getlist('documents[]')
            current_app.logger.info(f'收到 {len(document_paths)} 个文档URL')

        # 更新资产的图片路径
        if image_paths:
            try:
                asset.images = json.dumps(image_paths)
                current_app.logger.info(f'更新资产图片成功: {image_paths}')
                db.session.commit()
            except Exception as e:
                current_app.logger.error(f'保存图片路径失败: {str(e)}')
                raise
            
        if document_paths:
            asset.documents = json.dumps(document_paths)
            current_app.logger.info(f'更新资产文档成功: {document_paths}')
            
        if image_paths or document_paths:
            db.session.commit()
        
        return jsonify({
            'message': '资产创建成功',
            'assetId': asset.id
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'创建资产失败: {str(e)}', exc_info=True)
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

@api_bp.route('/assets/<int:asset_id>/dividend', methods=['POST'])
def create_dividend(asset_id):
    """创建分红记录"""
    try:
        # 检查资产是否存在
        asset = Asset.query.get_or_404(asset_id)
        
        # 检查请求者是否是资产所有者
        eth_address = request.headers.get('X-Eth-Address')
        if not eth_address or eth_address.lower() != asset.owner_address.lower():
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

@api_bp.route('/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件被上传'}), 400
            
        file = request.files['file']
        if not file:
            return jsonify({'error': '文件无效'}), 400
            
        # 检查文件大小
        file_data = file.read()
        file.seek(0)  # 重置文件指针
        
        if len(file_data) > 10 * 1024 * 1024:  # 10MB
            return jsonify({'error': '文件大小超过限制'}), 400
            
        # 获取资产类型和ID
        asset_type = request.form.get('asset_type', '10')  # 默认为不动产
        asset_id = request.form.get('asset_id', 'temp')  # 如果没有asset_id，使用temp目录
        file_type = request.form.get('file_type', 'images')  # 默认为图片
        
        # 构建文件路径
        ext = file.filename.rsplit(".", 1)[1].lower() if '.' in file.filename else ''
        filename = f'{asset_type}/{asset_id}/{file_type}/{int(time.time())}_{secure_filename(file.filename)}'
            
        # 获取存储服务实例
        from app.utils.storage import get_storage
        try:
            storage = get_storage()
            if not storage:
                raise ValueError('存储服务未初始化')
        except Exception as e:
            current_app.logger.error(f'获取存储服务失败: {str(e)}')
            raise ValueError('存储服务未准备就绪')
                
        # 上传文件到存储服务
        result = storage.upload(file_data, filename)
        if not result or 'url' not in result:
            raise Exception("文件上传失败")
            
        # 返回包含urls数组的响应
        return jsonify({
            'urls': [result['url']],
            'name': file.filename,
            'message': '上传成功'
        })
        
    except Exception as e:
        current_app.logger.error(f'文件上传失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/check_token_symbol', methods=['GET'])
def check_token_symbol():
    """检查代币符号是否已存在"""
    try:
        symbol = request.args.get('symbol')
        current_app.logger.info(f'检查代币符号: {symbol}')
        
        if not symbol:
            return jsonify({'error': '缺少代币符号参数'}), 400
            
        # 检查符号格式
        if not re.match(r'^RH-(?:10|20)\d{4}$', symbol):
            current_app.logger.warning(f'无效的代币符号格式: {symbol}')
            return jsonify({'error': '无效的代币符号格式'}), 400
            
        # 查询数据库，排除已删除的资产
        try:
            exists = db.session.query(db.exists().where(
                db.and_(
                    Asset.token_symbol == symbol,
                    Asset.status != AssetStatus.DELETED.value  # 使用状态字段检查
                )
            )).scalar()
            current_app.logger.info(f'代币符号 {symbol} 查询结果: {"存在" if exists else "不存在"}')
            
            # 如果存在，记录当前数据库中的所有未删除资产的代币符号
            if exists:
                existing_symbols = db.session.query(Asset.token_symbol).filter(
                    Asset.status != AssetStatus.DELETED.value
                ).all()
                current_app.logger.info(f'当前数据库中的代币符号: {[s[0] for s in existing_symbols]}')
            
            return jsonify({
                'exists': exists,
                'symbol': symbol
            })
            
        except Exception as e:
            current_app.logger.error(f'数据库查询失败: {str(e)}')
            return jsonify({'error': '数据库查询失败'}), 500
            
    except Exception as e:
        current_app.logger.error(f'检查代币符号失败: {str(e)}')
        return jsonify({'error': str(e)}), 500
