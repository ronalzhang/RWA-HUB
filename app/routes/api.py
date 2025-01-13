from flask import jsonify, request, g, current_app
from app.models.user import User
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.trade import Trade
from app import db
from . import auth_api_bp, assets_api_bp, trades_api_bp
from app.utils.decorators import token_required, eth_address_required
from .admin import is_admin
import os
import json
from werkzeug.utils import secure_filename

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 认证API路由
@auth_api_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '请提供用户名和密码'}), 400
        
    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': '用户名或密码错误'}), 401
        
    token = user.generate_token()
    return jsonify({'token': token, 'eth_address': user.eth_address}), 200

# 资产API路由
@assets_api_bp.route('/')
def list_assets():
    """获取资产列表"""
    try:
        # 获取管理员地址列表
        admin_addresses = list(current_app.config.get('ADMIN_ADDRESSES', set()))
        # 检查是否是管理员
        is_admin = hasattr(g, 'eth_address') and g.eth_address in admin_addresses
        
        # 如果是管理员，获取所有资产，否则只获取已审核通过的资产
        query = Asset.query if is_admin else Asset.query.filter_by(status=AssetStatus.APPROVED)
        
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

@assets_api_bp.route('/<int:asset_id>')
def get_asset(asset_id):
    """获取资产详情"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        # 如果资产已审核通过，直接允许访问
        if asset.status == AssetStatus.APPROVED:
            return jsonify(asset.to_dict()), 200
            
        # 获取管理员地址列表
        admin_addresses = [
            '0x6394993426DBA3b654eF0052698Fe9E0B6A98870',
            '0x124e5B8A4E6c68eC66e181E0B54817b12D879c57'
        ]
        
        # 从请求头、URL参数或cookie获取地址
        eth_address = request.headers.get('X-Eth-Address') or \
                     request.args.get('eth_address') or \
                     request.cookies.get('eth_address')
        
        if not eth_address:
            return jsonify({'error': '需要提供钱包地址'}), 401
        
        # 检查是否是管理员或资产所有者
        is_admin = eth_address.lower() in [addr.lower() for addr in admin_addresses]
        is_owner = eth_address.lower() == asset.owner_address.lower()
        
        # 如果是管理员或所有者，允许访问
        if is_admin or is_owner:
            return jsonify(asset.to_dict()), 200
            
        return jsonify({'error': '没有权限访问此资产'}), 403
        
    except Exception as e:
        current_app.logger.error(f'获取资产详情失败: {str(e)}', exc_info=True)
        return jsonify({'error': '获取资产详情失败'}), 500

@assets_api_bp.route('/', methods=['POST'])
@eth_address_required
def create_asset():
    if not request.form:
        return jsonify({'error': '请提供资产信息'}), 400
        
    required_fields = ['name', 'asset_type', 'token_price', 'location', 'token_code', 'annual_revenue']
    if not all(field in request.form for field in required_fields):
        return jsonify({'error': '请填写所有必要字段'}), 400
    
    try:
        # 处理资产类型和相关字段
        is_real_estate = request.form['asset_type'] == '10'
        area = float(request.form.get('area', 0)) if is_real_estate else None
        total_value = float(request.form.get('total_value', 0))
        
        # 计算代币发行量
        if is_real_estate:
            if not area or area <= 0:
                return jsonify({'error': '不动产必须输入有效的面积'}), 400
            token_supply = int(area * 10000)  # 不动产：每平方米10000个代币
        else:
            token_supply = int(request.form.get('token_supply', 0))
            if not token_supply or token_supply <= 0:
                return jsonify({'error': '类不动产必须输入有效的代币发行量'}), 400

        # 创建资产记录
        asset = Asset(
            name=request.form['name'],
            description=request.form.get('description'),
            asset_type=AssetType.REAL_ESTATE if is_real_estate else AssetType.SEMI_REAL_ESTATE,
            token_code=request.form['token_code'],
            token_symbol=f"RH-{request.form['token_code']}",
            token_price=float(request.form['token_price']),
            location=request.form['location'],
            area=area,
            total_value=total_value,
            token_supply=token_supply,  # 使用计算好的代币发行量
            annual_revenue=float(request.form['annual_revenue']),
            owner_address=g.eth_address,
            status=AssetStatus.PENDING
        )
        db.session.add(asset)
        db.session.flush()  # 获取资产ID
        
        # 创建资产目录
        asset_type = 'real_estate' if is_real_estate else 'quasi_real_estate'
        asset_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], asset_type, str(asset.id))
        os.makedirs(asset_dir, exist_ok=True)
        
        # 保存图片
        images = request.files.getlist('images')
        image_paths = []
        for i, image in enumerate(images):
            if image and allowed_file(image.filename):
                ext = os.path.splitext(image.filename)[1]
                filename = f'image_{i+1}{ext}'
                image_path = os.path.join(asset_dir, filename)
                image.save(image_path)
                image_paths.append(os.path.join('static', 'uploads', asset_type, str(asset.id), filename))
        
        asset.images = json.dumps(image_paths)
        
        # 保存文档
        documents = request.files.getlist('documents')
        doc_paths = []
        for i, doc in enumerate(documents):
            if doc and allowed_file(doc.filename):
                ext = os.path.splitext(doc.filename)[1]
                filename = f'doc_{i+1}{ext}'
                doc_path = os.path.join(asset_dir, filename)
                doc.save(doc_path)
                doc_paths.append(os.path.join('static', 'uploads', asset_type, str(asset.id), filename))
        
        asset.documents = json.dumps(doc_paths)
        
        db.session.commit()
        return jsonify(asset.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@assets_api_bp.route('/<int:asset_id>', methods=['PUT'])
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
        return jsonify({'message': f'保存失败: {str(e)}'}), 500

# 交易API路由
@trades_api_bp.route('/')
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

@trades_api_bp.route('/', methods=['POST'])
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