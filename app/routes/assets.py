from flask import render_template, send_from_directory, current_app, abort, request, redirect, url_for, jsonify, g, Response, flash
from . import assets_bp, assets_api_bp
from .. import db  # 直接从应用实例导入 db
from ..models import Asset
from ..models.asset import AssetStatus
from ..utils import is_admin, save_files
from ..utils.decorators import eth_address_required, admin_required, permission_required
from ..utils.storage import storage
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
@eth_address_required  # 添加钱包地址检查装饰器
def asset_detail_page(asset_id):
    """资产详情页面"""
    try:
        # 获取资产信息
        asset = Asset.query.get_or_404(asset_id)
        current_app.logger.info(f'获取资产信息成功: {asset.id}')
        
        # 获取分红历史
        dividend_records = asset.dividend_records if asset.dividend_records else []
        current_app.logger.info(f'获取分红记录: {len(dividend_records)} 条')
        
        # 使用全局钱包地址
        current_user_address = g.eth_address.lower() if g.eth_address else None
        current_app.logger.info(f'当前用户钱包地址: {current_user_address}')
        
        # 检查是否是管理员
        is_admin_user = is_admin(current_user_address)
        current_app.logger.info(f'是否是管理员: {is_admin_user}')
        
        # 检查是否是资产所有者
        is_owner = current_user_address and current_user_address == asset.owner_address.lower()
        current_app.logger.info(f'是否是资产所有者: {is_owner}')
        
        # 计算剩余可售数量
        remaining_supply = asset.token_supply
        if asset.token_address:
            # TODO: 从合约获取实际剩余数量
            pass
            
        return render_template("assets/detail.html", 
                             asset=asset,
                             dividend_records=dividend_records,
                             remaining_supply=remaining_supply,
                             current_user_address=current_user_address,
                             is_admin_user=is_admin_user,
                             is_owner=is_owner)
    except Exception as e:
        current_app.logger.error(f"获取资产详情失败: {str(e)}")
        abort(404)

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
@eth_address_required
def edit_asset_page(asset_id):
    """编辑资产页面"""
    try:
        # 获取资产信息
        asset = Asset.query.get_or_404(asset_id)
        
        # 检查权限
        is_owner = g.eth_address.lower() == asset.owner_address.lower()
        is_admin_user = is_admin(g.eth_address)
        
        if not (is_owner or is_admin_user):
            flash('您没有权限编辑此资产', 'error')
            return redirect(url_for('assets.list_assets_page'))
            
        return render_template('assets/edit.html', asset=asset)
    except Exception as e:
        current_app.logger.error(f'加载编辑资产页面失败: {str(e)}')
        flash('系统错误，请稍后重试', 'error')
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

@assets_bp.route('/<int:asset_id>/dividend')
@eth_address_required
def dividend_page(asset_id):
    """资产分红管理页面"""
    try:
        # 获取资产信息
        asset = Asset.query.get_or_404(asset_id)
        
        # 检查权限
        if not g.eth_address:
            flash('请先连接钱包', 'error')
            return redirect(url_for('assets.asset_detail_page', asset_id=asset_id))
            
        # 检查是否是管理员或资产所有者
        is_admin_user = is_admin(g.eth_address)
        is_owner = g.eth_address.lower() == asset.owner_address.lower()
        
        if not (is_admin_user or is_owner):
            flash('您没有权限访问分红管理页面', 'error')
            return redirect(url_for('assets.asset_detail_page', asset_id=asset_id))
            
        return render_template('assets/dividend.html', asset=asset)
    except Exception as e:
        current_app.logger.error(f'访问分红管理页面失败: {str(e)}')
        flash('访问分红管理页面失败')
        return redirect(url_for('assets.asset_detail_page', asset_id=asset_id))

def allowed_file(filename, allowed_extensions):
    """检查文件类型是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

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
