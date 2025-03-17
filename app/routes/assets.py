from flask import render_template, send_from_directory, current_app, abort, request, redirect, url_for, jsonify, g, Response, flash, session
from . import assets_bp, assets_api_bp
from app.extensions import db  # 从扩展模块导入 db
from app.models import Asset
from app.models.asset import AssetStatus, AssetType
from app.models.trade import Trade, TradeType, TradeStatus  # 添加Trade和交易状态枚举
from app.models.referral import UserReferral as NewUserReferral  # 使用新版UserReferral
from app.utils import is_admin, save_files
from app.utils.decorators import eth_address_required, admin_required, permission_required
from app.utils.storage import storage
import os
import json
from datetime import datetime
import random
import requests

# 页面路由
@assets_bp.route("/")
def list_assets_page():
    """资产列表页面"""
    try:
        # 获取当前用户的钱包地址（从多个来源）
        eth_address_header = request.headers.get('X-Eth-Address')
        eth_address_cookie = request.cookies.get('eth_address')
        eth_address_args = request.args.get('eth_address')
        
        current_user_address = eth_address_header or eth_address_cookie or eth_address_args
        
        # 详细日志记录
        current_app.logger.info(f'钱包地址来源:')
        current_app.logger.info(f'- Header: {eth_address_header}')
        current_app.logger.info(f'- Cookie: {eth_address_cookie}')
        current_app.logger.info(f'- Args: {eth_address_args}')
        current_app.logger.info(f'最终使用地址: {current_user_address}')
        
        # 检查是否是管理员
        is_admin_user = is_admin(current_user_address)
        current_app.logger.info(f'是否是管理员: {is_admin_user}')

        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = 9  # 每页显示9个资产

        # 构建基础查询
        query = Asset.query.filter(Asset.status != 0)  # 0 表示已删除
        
        # 记录原始查询结果数量
        total_count = query.count()
        current_app.logger.info(f'未过滤的资产总数: {total_count}')

        # 根据用户身份过滤资产
        if current_user_address:
            if is_admin_user:
                current_app.logger.info('管理员用户：显示所有未删除资产')
                # 管理员可以看到所有未删除的资产
                pass
            else:
                current_app.logger.info('普通用户：显示已审核通过的资产和自己的资产')
                # 普通用户：显示已审核通过的资产和自己的资产
                query = query.filter(
                    db.or_(
                        Asset.status == 2,  # 2 表示已审核通过
                        Asset.owner_address == current_user_address
                    )
                )
        else:
            current_app.logger.info('未登录用户：只显示已审核通过的资产')
            # 未登录用户：只显示已审核通过的资产
            query = query.filter(Asset.status == 2)  # 2 表示已审核通过

        # 记录过滤后的查询结果数量
        filtered_count = query.count()
        current_app.logger.info(f'过滤后的资产数量: {filtered_count}')

        # 按创建时间倒序排序
        query = query.order_by(Asset.created_at.desc())

        # 执行分页查询
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        assets = pagination.items

        # 记录每个资产的详细信息
        current_app.logger.info(f'当前页面资产列表 ({len(assets)} 个):')
        for asset in assets:
            current_app.logger.info(
                f'- ID: {asset.id}, '
                f'名称: {asset.name}, '
                f'状态: {asset.status}, '
                f'所有者: {asset.owner_address}, '
                f'创建时间: {asset.created_at}'
            )

        # 渲染模板
        return render_template('assets/list.html', 
                             assets=assets, 
                             pagination=pagination,
                             current_user_address=current_user_address,
                             is_admin=is_admin_user)

    except Exception as e:
        current_app.logger.error(f'获取资产列表失败: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())  # 添加详细的错误堆栈
        return render_template('assets/list.html', 
                             assets=[], 
                             pagination=None,
                             current_user_address=current_user_address,
                             is_admin=is_admin_user)

@assets_bp.route("/<int:asset_id>")
def asset_detail_page(asset_id):
    """资产详情页面 - 使用ID (旧版,保留兼容性)"""
    try:
        current_app.logger.info(f'通过ID访问资产详情，ID: {asset_id}')
        
        # 获取资产信息
        asset = Asset.query.get_or_404(asset_id)
        
        # 转向新格式URL
        return redirect(url_for('assets.asset_detail_by_symbol', token_symbol=asset.token_symbol), code=301)
    except Exception as e:
        current_app.logger.error(f'获取资产详情失败: {str(e)}')
        flash('获取资产详情失败，请稍后重试', 'error')
        return redirect(url_for('assets.list_assets_page'))

@assets_bp.route("/<string:token_symbol>")
def asset_detail_by_symbol(token_symbol):
    """资产详情页面 - 使用token_symbol"""
    try:
        current_app.logger.info(f'访问资产详情页面，Token Symbol: {token_symbol}')
        
        # 获取资产信息
        asset = Asset.query.filter_by(token_symbol=token_symbol).first_or_404()
        
        # 获取用户钱包地址
        current_user_address = get_eth_address()
        
        # 处理推荐人参数
        referrer = request.args.get('ref') or request.args.get('referrer')
        if referrer and current_user_address and referrer != current_user_address:
            try:
                # 记录推荐关系
                # 检查是否已存在推荐关系，避免重复记录
                existing_referral = NewUserReferral.query.filter_by(
                    user_address=current_user_address
                ).first()
                
                if not existing_referral:
                    # 创建新的推荐关系
                    new_referral = NewUserReferral(
                        user_address=current_user_address,
                        referrer_address=referrer,
                        referral_time=datetime.now(),
                        asset_id=asset.id,
                        status='active'
                    )
                    db.session.add(new_referral)
                    db.session.commit()
                    current_app.logger.info(f'已创建推荐关系: {referrer} -> {current_user_address}')
            except Exception as e:
                current_app.logger.error(f'记录推荐关系失败: {str(e)}')
        
        # 检查是否是管理员
        is_admin_user = is_admin(current_user_address) if current_user_address else False
        current_app.logger.info(f'是否是管理员: {is_admin_user}')
        
        # 检查是否是资产所有者
        is_owner = False
        if current_user_address and asset.owner_address:
            # 区分ETH和SOL地址处理
            if current_user_address.startswith('0x') and asset.owner_address.startswith('0x'):
                # ETH地址比较（不区分大小写）
                is_owner = current_user_address.lower() == asset.owner_address.lower()
            else:
                # SOL地址比较（区分大小写）
                is_owner = current_user_address == asset.owner_address
            
            current_app.logger.info(f'是否是资产所有者: {is_owner}')
        
        # 计算剩余供应量
        if asset.remaining_supply is not None:
            # 优先使用数据库存储的剩余供应量
            remaining_supply = asset.remaining_supply
        else:
            # 如果没有剩余供应量数据，使用总供应量
            remaining_supply = asset.token_supply
        
        current_app.logger.info(f'资产 {asset.id} 剩余供应量: {remaining_supply}')
        
        # 获取资产累计分红数据
        try:
            from app.models import Dividend
            
            # 查询所有已确认的分红记录
            dividends = Dividend.query.filter_by(
                asset_id=asset.id, 
                status='confirmed'
            ).all()
            
            # 计算累计分红金额
            total_dividends = sum(dividend.amount for dividend in dividends)
            current_app.logger.info(f'资产 {asset.id} 累计分红: {total_dividends} USDC')
        except Exception as e:
            current_app.logger.error(f'获取累计分红数据失败: {str(e)}')
            total_dividends = 0
        
        # 渲染详情页面
        return render_template('assets/detail.html', 
                              asset=asset, 
                              remaining_supply=remaining_supply,
                              is_owner=is_owner,
                              is_admin_user=is_admin_user,
                              current_user_address=current_user_address,
                              total_dividends=total_dividends)
                              
    except Exception as e:
        current_app.logger.error(f"访问资产详情页面失败: {str(e)}", exc_info=True)
        flash(_('Failed to access asset detail page'), 'danger')
        return redirect(url_for('assets.list_assets_page'))

@assets_bp.route('/create')
@eth_address_required
def create_asset_page():
    """创建资产页面"""
    try:
        # 检查钱包连接状态
        if not g.eth_address:
            flash('请先连接钱包', 'error')
            return redirect(url_for('main.index'))
            
        # 记录创建者地址
        current_app.logger.info(f'用户 {g.eth_address} 访问创建资产页面')
        return render_template('assets/create.html', creator_address=g.eth_address)
    except Exception as e:
        current_app.logger.error(f'加载创建资产页面失败: {str(e)}')
        flash('系统错误，请稍后重试', 'error')
        return redirect(url_for('main.index'))

@assets_bp.route('/<int:asset_id>/edit')
def edit_asset_page(asset_id):
    """资产编辑页面 - 使用ID（旧版，保留兼容性）"""
    try:
        current_app.logger.info(f"使用ID访问资产编辑页面，ID: {asset_id}")
        # 重定向到新的URL格式
        asset = Asset.query.get_or_404(asset_id)
        return redirect(url_for('assets.edit_asset_by_symbol', token_symbol=asset.token_symbol))
    except Exception as e:
        current_app.logger.error(f"访问资产编辑页面失败: {str(e)}", exc_info=True)
        flash('访问资产编辑页面失败', 'danger')
        return redirect(url_for('assets.list_assets_page'))

@assets_bp.route("/<string:token_symbol>/edit")
def edit_asset_by_symbol(token_symbol):
    """编辑资产页面 - 使用token_symbol"""
    try:
        # 获取资产信息
        asset = Asset.query.filter_by(token_symbol=token_symbol).first_or_404()
        
        # 获取用户钱包地址（多来源）
        eth_address_header = request.headers.get('X-Eth-Address')
        eth_address_cookie = request.cookies.get('eth_address')
        eth_address_session = session.get('eth_address')
        eth_address_arg = request.args.get('eth_address')
        
        # 按优先级获取钱包地址
        eth_address = eth_address_header or eth_address_cookie or eth_address_session or eth_address_arg
        
        # 记录所有来源的钱包地址
        current_app.logger.info(f'编辑页面 - 钱包地址来源:')
        current_app.logger.info(f'- Header: {eth_address_header}')
        current_app.logger.info(f'- Cookie: {eth_address_cookie}')
        current_app.logger.info(f'- Session: {eth_address_session}')
        current_app.logger.info(f'- URL参数: {eth_address_arg}')
        current_app.logger.info(f'- 最终使用: {eth_address}')
        
        if not eth_address:
            current_app.logger.warning(f"访问编辑页面被拒绝：未提供钱包地址")
            flash('请先连接钱包以编辑资产', 'warning')
            return redirect(url_for('assets.asset_detail_by_symbol', token_symbol=token_symbol))
            
        # 检查是否是管理员或资产所有者
        is_admin_user = is_admin(eth_address)
        
        # 检查是否是资产所有者，区分ETH和SOL地址
        is_owner = False
        if asset.owner_address:
            # 对ETH地址（0x开头）忽略大小写比较
            if eth_address.startswith('0x') and asset.owner_address.startswith('0x'):
                is_owner = eth_address.lower() == asset.owner_address.lower()
            # 对SOL地址严格区分大小写
            else:
                is_owner = eth_address == asset.owner_address
        
        current_app.logger.info(f'用户 {eth_address} 访问编辑页面: 是管理员={is_admin_user}, 是所有者={is_owner}')
        
        if not (is_admin_user or is_owner):
            current_app.logger.warning(f"非管理员或所有者访问尝试：{eth_address}")
            flash('您没有权限编辑此资产', 'danger')
            return redirect(url_for('assets.asset_detail_by_symbol', token_symbol=token_symbol))
        
        # 如果资产已上链，不允许编辑
        if asset.token_address:
            flash('已上链资产无法修改', 'warning')
            return redirect(url_for('assets.asset_detail_by_symbol', token_symbol=token_symbol))
        
        # 渲染编辑页面
        return render_template('assets/edit.html', asset=asset, can_edit=True)
        
    except Exception as e:
        current_app.logger.error(f"访问资产编辑页面失败: {str(e)}", exc_info=True)
        flash('访问资产编辑页面失败', 'danger')
        return redirect(url_for('assets.list_assets_page'))

@assets_bp.route('/proxy/<string:file_type>/<path:file_path>')
def proxy_file(file_type, file_path):
    """处理文件请求"""
    try:
        # 检查是否是静态资源路径
        if file_path.startswith('static/'):
            return send_from_directory('static', file_path[7:])
            
        # 检查是否是上传的文件
        if file_path.startswith('uploads/'):
            return send_from_directory('static/uploads', file_path[8:])
            
        # 如果都不是，返回404
        current_app.logger.error(f"文件不存在: {file_path}")
        abort(404)
            
    except Exception as e:
        current_app.logger.error(f"文件请求失败: {str(e)}")
        abort(500)

@assets_bp.route('/proxy/image/<path:image_path>')
def proxy_image(image_path):
    """处理图片请求"""
    try:
        # 检查是否是静态资源路径
        if image_path.startswith('static/'):
            return send_from_directory('static', image_path[7:])
            
        # 检查是否是上传的文件
        if image_path.startswith('uploads/'):
            return send_from_directory('static/uploads', image_path[8:])
            
        # 如果都不是，返回默认图片
        return send_from_directory('static/images', 'placeholder.jpg')
            
    except Exception as e:
        current_app.logger.error(f"图片请求失败: {str(e)}")
        return send_from_directory('static/images', 'placeholder.jpg')

@assets_api_bp.route('/generate-token-symbol', methods=['POST'])
def generate_token_symbol():
    """生成代币代码"""
    try:
        data = request.get_json()
        asset_type = data.get('type')
        
        if not asset_type:
            return jsonify({'error': '缺少资产类型'}), 400
            
        # 生成随机数
        random_num = f"{random.randint(0, 9999):04d}"
        token_symbol = f"RH-{asset_type}{random_num}"
        
        return jsonify({
            'token_symbol': token_symbol
        })
    except Exception as e:
        current_app.logger.error(f'生成代币代码失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

@assets_api_bp.route('/calculate-tokens', methods=['POST'])
def calculate_tokens():
    """计算代币数量和价格"""
    try:
        data = request.get_json()
        asset_type = data.get('type')
        area = float(data.get('area', 0))
        total_value = float(data.get('total_value', 0))
        
        if asset_type == '10':  # 不动产
            token_count = area * 10000  # 每平方米10000个代币
            token_price = total_value / token_count if token_count > 0 else 0
        else:  # 类不动产
            token_count = int(data.get('token_count', 0))
            token_price = total_value / token_count if token_count > 0 else 0
            
        return jsonify({
            'token_count': int(token_count),
            'token_price': round(token_price, 6)
        })
    except Exception as e:
        current_app.logger.error(f'计算代币数量和价格失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

@assets_api_bp.route('/upload', methods=['POST'])
@eth_address_required
def upload_files():
    """上传文件"""
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            current_app.logger.error('没有文件被上传')
            return jsonify({'error': '没有文件被上传'}), 400
            
        file = request.files['file']
        if not file:
            current_app.logger.error('文件无效')
            return jsonify({'error': '文件无效'}), 400
            
        asset_type = request.form.get('asset_type')
        file_type = request.form.get('file_type', 'image')
        asset_id = request.form.get('asset_id', 'temp')
        
        current_app.logger.info(f'开始上传文件: {file.filename}')
        current_app.logger.info(f'资产类型: {asset_type}')
        current_app.logger.info(f'文件类型: {file_type}')
        current_app.logger.info(f'资产ID: {asset_id}')
        
        if not asset_type:
            current_app.logger.error('缺少资产类型')
            return jsonify({'error': '缺少资产类型'}), 400
            
        # 保存文件
        file_urls = save_files([file], asset_type, asset_id)
        
        if not file_urls:
            current_app.logger.error('文件上传失败')
            return jsonify({'error': '文件上传失败'}), 500
            
        current_app.logger.info(f'文件上传成功: {file_urls}')
        return jsonify({
            'urls': file_urls
        })
    except Exception as e:
        current_app.logger.error(f'上传文件失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

@assets_api_bp.route('/<int:asset_id>/check_owner')
@eth_address_required
def check_asset_owner(asset_id):
    """检查用户是否是资产所有者或管理员"""
    try:
        # 获取资产信息
        asset = Asset.query.get_or_404(asset_id)
        
        # 检查权限
        if not g.eth_address:
            return jsonify({
                'is_owner': False,
                'is_admin': False,
                'error': '未提供钱包地址'
            }), 200
            
        # 检查是否是管理员或资产所有者
        is_admin_user = is_admin(g.eth_address)
        
        owner_address = asset.owner_address
        user_address = g.eth_address
        
        # 区分ETH和SOL地址的比较
        if owner_address.startswith('0x') and user_address.startswith('0x'):
            # ETH地址比较时都转为小写
            is_owner = user_address.lower() == owner_address.lower()
        else:
            # SOL地址或其他类型地址直接比较（大小写敏感）
            is_owner = user_address == owner_address
        
        return jsonify({
            'is_owner': is_owner,
            'is_admin': is_admin_user
        }), 200
    except Exception as e:
        current_app.logger.error(f'检查资产所有权失败: {str(e)}')
        return jsonify({
            'is_owner': False,
            'is_admin': False,
            'error': str(e)
        }), 500

def allowed_file(filename, allowed_extensions):
    """检查文件类型是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@assets_bp.route('/<string:token_symbol>/dividend')
def dividend_page_by_symbol(token_symbol):
    """资产分红页面 - 使用token_symbol"""
    try:
        # 获取资产信息
        asset = Asset.query.filter_by(token_symbol=token_symbol).first_or_404()
        
        # 获取用户钱包地址（多来源）
        eth_address_header = request.headers.get('X-Eth-Address')
        eth_address_cookie = request.cookies.get('eth_address')
        eth_address_session = session.get('eth_address')
        eth_address_arg = request.args.get('eth_address')
        
        # 按优先级获取钱包地址
        eth_address = eth_address_header or eth_address_cookie or eth_address_session or eth_address_arg
        
        # 记录所有来源的钱包地址
        current_app.logger.info(f'分红页面 - 钱包地址来源:')
        current_app.logger.info(f'- Header: {eth_address_header}')
        current_app.logger.info(f'- Cookie: {eth_address_cookie}')
        current_app.logger.info(f'- Session: {eth_address_session}')
        current_app.logger.info(f'- URL参数: {eth_address_arg}')
        current_app.logger.info(f'- 最终使用: {eth_address}')
        
        if not eth_address:
            current_app.logger.warning(f"访问分红页面被拒绝：未提供钱包地址")
            flash('请先连接钱包以管理分红', 'warning')
            return redirect(url_for('assets.asset_detail_by_symbol', token_symbol=token_symbol))
            
        # 检查是否是管理员或资产所有者
        is_admin_user = is_admin(eth_address)
        
        # 检查是否是资产所有者，区分ETH和SOL地址
        is_owner = False
        if asset.owner_address:
            # 对ETH地址（0x开头）忽略大小写比较
            if eth_address.startswith('0x') and asset.owner_address.startswith('0x'):
                is_owner = eth_address.lower() == asset.owner_address.lower()
            # 对SOL地址严格区分大小写
            else:
                is_owner = eth_address == asset.owner_address
        
        current_app.logger.info(f'用户 {eth_address} 访问分红页面: 是管理员={is_admin_user}, 是所有者={is_owner}')
        
        if not (is_admin_user or is_owner):
            current_app.logger.warning(f"非管理员或所有者访问尝试：{eth_address}")
            flash('您没有权限管理此资产的分红', 'danger')
            return redirect(url_for('assets.asset_detail_by_symbol', token_symbol=token_symbol))
        
        # 渲染分红页面
        return render_template('assets/dividend.html', 
                              asset=asset, 
                              can_manage=True)
                              
    except Exception as e:
        current_app.logger.error(f"访问资产分红页面失败: {str(e)}", exc_info=True)
        flash('访问资产分红页面失败', 'danger')
        return redirect(url_for('assets.list_assets_page'))

# 全局前置处理器，确保在所有处理之前捕获重复前缀问题
def register_global_handlers(app):
    """注册全局处理器"""
    @app.before_request
    def check_duplicate_assets_prefix():
        """捕获所有请求中的重复assets前缀问题"""
        if request.path and '/assets/assets/' in request.path:
            current_app.logger.warning(f'全局检测到重复assets路径: {request.path}')
            # 将/assets/assets/替换为/assets/
            corrected_path = request.path.replace('/assets/assets/', '/assets/')
            current_app.logger.info(f'全局修正后路径: {corrected_path}')
            return redirect(corrected_path, code=301)
        return None

def get_eth_address():
    """从多个来源获取钱包地址"""
    # 记录各个来源的钱包地址情况
    eth_address_header = request.headers.get('X-Eth-Address')
    eth_address_cookie = request.cookies.get('eth_address')
    eth_address_session = session.get('eth_address')
    eth_address_g = g.eth_address if hasattr(g, 'eth_address') else None
    eth_address_arg = request.args.get('eth_address')
    
    current_app.logger.info('钱包地址来源:')
    current_app.logger.info(f'- Header: {eth_address_header}')
    current_app.logger.info(f'- Cookie: {eth_address_cookie}')
    current_app.logger.info(f'- Session: {eth_address_session}')
    current_app.logger.info(f'- g对象: {eth_address_g}')
    current_app.logger.info(f'- URL参数: {eth_address_arg}')
    
    # 按优先级获取钱包地址
    eth_address = eth_address_header or eth_address_cookie or eth_address_session or eth_address_g or eth_address_arg
    
    if not eth_address:
        current_app.logger.warning('未提供钱包地址')
    else:
        # 处理不同类型的地址
        if eth_address.startswith('0x'):
            # ETH地址统一转为小写
            eth_address = eth_address.lower()
        # SOL地址保持原样，因为它是大小写敏感的
        
        current_app.logger.info(f'最终使用地址: {eth_address}')
    
    return eth_address
