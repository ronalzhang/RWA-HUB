from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, abort, session, jsonify, current_app, g, 
    make_response, send_file, stream_with_context, Response, send_from_directory
)
from flask_babel import _  # 添加此行导入
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
import re
import mimetypes
from app.config import Config
from app.utils.config_manager import ConfigManager
import traceback
import uuid
import time
import logging
from sqlalchemy import text
import qrcode
from io import BytesIO
from threading import Thread

# 页面路由
@assets_bp.route("/")
def list_assets_page():
    """资产列表页面"""
    try:
        # 获取当前用户的钱包地址（从多个来源）
        eth_address_header = request.headers.get('X-Eth-Address')
        eth_address_cookie = request.cookies.get('eth_address')
        eth_address_args = request.args.get('eth_address')
        
        # 优先使用 Args > Header > Cookie
        current_user_address = eth_address_args or eth_address_header or eth_address_cookie
        
        # 详细日志记录
        current_app.logger.info(f'钱包地址来源:')
        current_app.logger.info(f'- Header: {eth_address_header}')
        current_app.logger.info(f'- Cookie: {eth_address_cookie}')
        current_app.logger.info(f'- Args: {eth_address_args}')
        current_app.logger.info(f'最终使用地址: {current_user_address}')
        
        # 检查是否是管理员
        is_admin_user = is_admin(current_user_address)
        current_app.logger.info(f'是否是管理员: {is_admin_user}, 地址: {current_user_address}')

        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = 9  # 每页显示9个资产

        # 构建基础查询
        query = Asset.query
        
        # 根据用户身份过滤资产
        if current_user_address and is_admin_user:
            current_app.logger.info('管理员用户：显示所有未删除资产')
            # 管理员可以看到所有未删除的资产
            query = query.filter(Asset.deleted_at.is_(None))
        else:
            current_app.logger.info('普通用户或未登录用户：只显示已上链且未删除的资产')
            # 普通用户或未登录用户：只显示已上链且未删除的资产
            query = query.filter(
                Asset.status == AssetStatus.ON_CHAIN.value,
                Asset.deleted_at.is_(None)
            )
            
            # 额外日志记录，确保过滤器有效
            count_before = Asset.query.count()
            count_after = query.count()
            current_app.logger.info(f'过滤前总资产数: {count_before}, 过滤后资产数: {count_after}')
        
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
        current_app.logger.warning(f'获取资产列表失败: {str(e)}')
        current_app.logger.warning(traceback.format_exc())  # 添加详细的错误堆栈
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
        current_app.logger.warning(f'获取资产详情失败: {str(e)}')
        flash('获取资产详情失败，请稍后重试', 'warning')
        return redirect(url_for('assets.list_assets_page'))

@assets_bp.route("/<string:token_symbol>")
def asset_detail_by_symbol(token_symbol):
    """资产详情页面 - 使用token_symbol"""
    try:
        # 添加更详细的日志
        current_app.logger.info(f'[DETAIL_PAGE_START] 访问资产详情页面，Token Symbol: {token_symbol}')
        current_app.logger.info(f'[DETAIL_PAGE_DEBUG] URL路径: {request.path}, User-Agent: {request.headers.get("User-Agent")}')
        
        # 获取资产信息
        asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if not asset:
            current_app.logger.error(f'[DETAIL_PAGE_ERROR] 资产不存在: {token_symbol}')
            flash(_('Asset not found'), 'danger')
            return render_template('error.html', error=_('Asset not found')), 404
            
        current_app.logger.info(f'[DETAIL_PAGE_DEBUG] 找到资产: ID={asset.id}, 名称={asset.name}, 状态={asset.status}')
        
        # 获取用户钱包地址
        current_user_address = get_eth_address()
        
        # 处理推荐人参数
        referrer = request.args.get('ref') or request.args.get('referrer')
        if referrer and current_user_address and referrer != current_user_address:
            try:
                existing_referral = NewUserReferral.query.filter_by(
                    user_address=current_user_address
                ).first()
                if not existing_referral:
                    new_referral = NewUserReferral(
                        user_address=current_user_address,
                        referrer_address=referrer,
                        referral_time=datetime.now(),
                        asset_id=asset.id,
                        status='active'
                    )
                    db.session.add(new_referral)
                    db.session.commit()
                    current_app.logger.info(f'[DETAIL_PAGE_REFERRAL] 已创建推荐关系: {referrer} -> {current_user_address}')
            except Exception as ref_e:
                current_app.logger.error(f'[DETAIL_PAGE_REFERRAL_ERROR] 记录推荐关系失败: {str(ref_e)}')
        
        # 检查是否是管理员
        is_admin_user = is_admin(current_user_address) if current_user_address else False
        
        # 检查是否是资产所有者
        is_owner = False
        if current_user_address and asset.owner_address:
            if current_user_address.startswith('0x') and asset.owner_address.startswith('0x'):
                is_owner = current_user_address.lower() == asset.owner_address.lower()
            else:
                is_owner = current_user_address == asset.owner_address
            
        # 计算剩余供应量
        if asset.remaining_supply is not None:
            remaining_supply = asset.remaining_supply
        else:
            remaining_supply = asset.token_supply
        
        # 获取资产累计分红数据
        total_dividends = 0
        try:
            # 直接使用SQL查询，避免payment_token字段不存在的问题
            sql = text("SELECT SUM(amount) FROM dividends WHERE asset_id = :asset_id AND status = 'confirmed'")
            result = db.session.execute(sql, {"asset_id": asset.id}).fetchone()
            total_dividends = result[0] if result[0] else 0
        except Exception as div_e:
            current_app.logger.error(f'[DETAIL_PAGE_DIVIDEND_ERROR] 获取累计分红数据失败: {str(div_e)}')
        
        # 获取分红记录数量，用于决定是否显示分红信息模块
        dividend_records_count = 0
        try:
            from app.models.dividend import DividendRecord
            dividend_records_count = DividendRecord.get_count_by_asset(asset.id)
        except Exception as dividend_count_e:
            current_app.logger.error(f'[DETAIL_PAGE_DIVIDEND_COUNT_ERROR] 获取分红记录数量失败: {str(dividend_count_e)}')

        # Log right before rendering
        current_app.logger.info(f'[DETAIL_PAGE_RENDER_START] 准备渲染模板 detail.html for {token_symbol}.')
        context = {
            'asset': asset,
            'remaining_supply': remaining_supply,
            'is_owner': is_owner,
            'is_admin_user': is_admin_user,
            'current_user_address': current_user_address,
            'total_dividends': total_dividends,
            'dividend_records_count': dividend_records_count,
            'platform_fee_address': ConfigManager.get_platform_fee_address(),
            'PLATFORM_FEE_RATE': getattr(Config, 'PLATFORM_FEE_RATE', 0.035)
        }
        current_app.logger.info(f'[DETAIL_PAGE_CONTEXT] Context keys: {list(context.keys())}')

        # 直接返回渲染的HTML，避免任何重定向
        return render_template('assets/detail.html', **context)
                              
    except Exception as e:
        # Log the exception
        current_app.logger.error(f'[DETAIL_PAGE_EXCEPTION] 访问资产详情页面 {token_symbol} 时捕获到异常!')
        current_app.logger.exception(e)
        
        # 添加具体错误信息到日志中
        tb_info = traceback.format_exc()
        current_app.logger.error(f'[DETAIL_PAGE_ERROR] 详细错误信息:\n{tb_info}')
        
        # 渲染错误页面而不是重定向
        return render_template('error.html', error=_('Error accessing asset details')), 500

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
        current_app.logger.warning(f'加载创建资产页面失败: {str(e)}')
        flash('系统错误，请稍后重试', 'warning')
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
        current_app.logger.warning(f"访问资产编辑页面失败: {str(e)}", exc_info=True)
        flash('访问资产编辑页面失败', 'warning')
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
            flash('您没有权限编辑此资产', 'warning')
            return redirect(url_for('assets.asset_detail_by_symbol', token_symbol=token_symbol))
        
        # 如果资产已上链，不允许编辑
        if asset.token_address:
            flash('已上链资产无法修改', 'warning')
            return redirect(url_for('assets.asset_detail_by_symbol', token_symbol=token_symbol))
        
        # 渲染编辑页面
        return render_template('assets/edit.html', asset=asset, can_edit=True)
        
    except Exception as e:
        current_app.logger.warning(f"访问资产编辑页面失败: {str(e)}", exc_info=True)
        flash('访问资产编辑页面失败', 'warning')
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
        current_app.logger.warning(f"文件不存在: {file_path}")
        abort(404)
            
    except Exception as e:
        current_app.logger.warning(f"文件请求失败: {str(e)}")
        abort(500)

@assets_bp.route('/proxy-image/<path:image_path>')
def proxy_image(image_path):
    """
    代理图片请求，支持多种路径格式
    """
    try:
        import os
        from flask import send_file, current_app, request, abort
        
        current_app.logger.info(f"请求代理图片: {image_path}")
        
        # 正常化路径 (移除多余的斜杠)
        image_path = os.path.normpath(image_path)
        
        # 列出尝试的所有路径，用于调试
        search_paths = []
        
        # 检查image_path是否包含完整的路径信息
        if image_path.startswith('uploads/'):
            file_path = os.path.join(current_app.static_folder, image_path)
            search_paths.append(file_path)
        elif image_path.startswith('projects/'):
            file_path = os.path.join(current_app.static_folder, 'uploads', image_path)
            search_paths.append(file_path)
        elif '/' in image_path:
            # 可能是旧格式路径，如: 10/temp/image/filename.jpg
            file_path = os.path.join(current_app.static_folder, 'uploads', image_path)
            search_paths.append(file_path)
            
            # 尝试在projects目录下查找
            if 'temp/image' in image_path:
                filename = os.path.basename(image_path)
                token_symbol = request.args.get('token', '')
                if token_symbol:
                    projects_path = os.path.join(current_app.static_folder, 'uploads', 'projects', token_symbol, 'images', filename)
                    search_paths.append(projects_path)
        else:
            # 单一文件名，尝试在多个位置查找
            filename = image_path
            token_symbol = request.args.get('token', '')
            
            # 尝试的路径列表
            possible_paths = []
            
            # 如果提供了token_symbol, 首先在该token的专属目录查找
            if token_symbol:
                possible_paths.append(os.path.join(current_app.static_folder, 'uploads', 'projects', token_symbol, 'images', filename))
            
            # 其他可能的路径
            possible_paths.extend([
                os.path.join(current_app.static_folder, 'uploads', '10', 'temp', 'image', filename),
                os.path.join(current_app.static_folder, 'uploads', '20', 'temp', 'image', filename),
                os.path.join(current_app.static_folder, 'uploads', 'temp', 'images', filename),
                os.path.join(current_app.static_folder, 'uploads', 'projects', 'temp', 'images', filename)
            ])
            
            search_paths.extend(possible_paths)
            
            # 查找第一个存在的文件
            for path in possible_paths:
                if os.path.isfile(path):
                    file_path = path
                    break
            else:
                current_app.logger.warning(f"找不到图片: {image_path}")
                current_app.logger.warning(f"尝试的路径: {search_paths}")
                abort(404)
        
        current_app.logger.info(f"尝试提供文件: {file_path}")
        
        # 检查文件是否存在
        if not os.path.isfile(file_path):
            current_app.logger.warning(f"文件不存在: {file_path}")
            
            # 搜索整个uploads目录
            import glob
            filename = os.path.basename(image_path)
            global_search = glob.glob(os.path.join(current_app.static_folder, 'uploads', '**', filename), recursive=True)
            
            if global_search:
                file_path = global_search[0]
                current_app.logger.info(f"全局搜索找到文件: {file_path}")
            else:
                current_app.logger.warning(f"尝试的所有路径: {search_paths}")
                current_app.logger.warning(f"全局搜索未找到文件: {filename}")
                abort(404)
        
        # 检查文件权限
        if not os.access(file_path, os.R_OK):
            current_app.logger.warning(f"文件无读取权限: {file_path}")
            abort(403)
        
        # 获取MIME类型
        import mimetypes
        mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        
        # 禁用浏览器缓存
        response = send_file(file_path, mimetype=mime_type)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        current_app.logger.info(f"成功代理图片: {image_path} -> {file_path}")
        return response
        
    except Exception as e:
        import traceback
        current_app.logger.warning(f"代理图片错误: {str(e)}")
        current_app.logger.warning(traceback.format_exc())
        abort(500)

@assets_api_bp.route('/generate-token-symbol', methods=['POST'])
def generate_token_symbol():
    """生成代币代码"""
    try:
        data = request.get_json()
        asset_type = data.get('type')
        
        if not asset_type:
            return jsonify({'error': '缺少资产类型'}), 400
            
        # 尝试多次生成唯一的token_symbol
        max_attempts = 10
        for attempt in range(max_attempts):
            # 生成随机数
            random_num = f"{random.randint(0, 9999):04d}"
            token_symbol = f"RH-{asset_type}{random_num}"
            
            # 检查是否已存在
            current_app.logger.info(f"尝试生成token_symbol: {token_symbol} (尝试 {attempt+1}/{max_attempts})")
            existing_asset = Asset.query.filter_by(token_symbol=token_symbol).first()
            
            # 如果不存在，则可以使用
            if not existing_asset:
                current_app.logger.info(f"生成的token_symbol可用: {token_symbol}")
                return jsonify({
                    'success': True,
                    'token_symbol': token_symbol
                })
            else:
                current_app.logger.warning(f"token_symbol已存在: {token_symbol}，重新生成")
        
        # 如果达到最大尝试次数仍未生成唯一符号，返回错误
        return jsonify({
            'success': False,
            'error': '无法生成唯一的代币符号，请稍后重试'
        }), 500
    except Exception as e:
        current_app.logger.error(f'生成代币代码失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

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
    """上传文件 (保留用于向后兼容)"""
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
        token_symbol = request.form.get('token_symbol', '')
        
        current_app.logger.info(f'开始上传文件: {file.filename}')
        current_app.logger.info(f'资产类型: {asset_type}')
        current_app.logger.info(f'文件类型: {file_type}')
        current_app.logger.info(f'资产ID: {asset_id}')
        current_app.logger.info(f'代币符号: {token_symbol}')
        
        if not asset_type:
            current_app.logger.error('缺少资产类型')
            return jsonify({'error': '缺少资产类型'}), 400
            
        # 保存文件
        file_urls = save_files([file], asset_type, asset_id, token_symbol)
        
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

@assets_api_bp.route('/upload-images', methods=['POST'])
def upload_images():
    """上传图片或文档（新API）"""
    try:
        current_app.logger.info('开始新上传API请求')
        
        # 检查请求大小
        content_length = request.content_length
        if content_length and content_length > 20 * 1024 * 1024:  # 限制为20MB
            current_app.logger.error(f'请求体太大: {content_length / (1024 * 1024):.2f}MB')
            return jsonify({'success': False, 'message': f'文件大小超过限制（最大20MB）, 当前: {content_length / (1024 * 1024):.2f}MB'}), 413
            
        # 检查是否有文件上传
        if 'file' not in request.files:
            current_app.logger.error('没有文件被上传')
            return jsonify({'success': False, 'message': '没有文件被上传'}), 400
            
        file = request.files['file']
        if not file:
            current_app.logger.error('文件无效')
            return jsonify({'success': False, 'message': '文件无效'}), 400
            
        # 检查文件大小
        file_content = file.read()
        file.seek(0)  # 重置文件指针
        
        file_size = len(file_content)
        if file_size > 5 * 1024 * 1024:  # 5MB
            current_app.logger.error(f'文件太大: {file_size / (1024 * 1024):.2f}MB')
            return jsonify({'success': False, 'message': f'文件大小超过限制（最大5MB），当前大小: {file_size / (1024 * 1024):.2f}MB'}), 413
            
        # 获取参数
        asset_type = request.form.get('asset_type')
        file_type = request.form.get('fileType', 'IMAGE')  # 注意前端使用fileType而不是file_type
        asset_id = request.form.get('asset_id', 'temp')
        token_symbol = request.form.get('token_symbol', '')
        
        current_app.logger.info(f'上传文件详情: 名称={file.filename}, 大小={file_size/1024:.2f}KB')
        current_app.logger.info(f'资产类型: {asset_type}, 文件类型: {file_type}, 资产ID: {asset_id}, 代币符号: {token_symbol}')
        
        # 检查token_symbol有效性，避免特殊字符导致目录问题
        if token_symbol and not re.match(r'^[A-Za-z0-9\-_]+$', token_symbol):
            current_app.logger.error(f'无效的token_symbol格式: {token_symbol}')
            return jsonify({'success': False, 'message': f'无效的代币符号格式: {token_symbol}，仅允许字母、数字、连字符和下划线'}), 400
        
        if not asset_type:
            current_app.logger.error('缺少资产类型')
            return jsonify({'success': False, 'message': '缺少资产类型参数'}), 400
            
        # 确保上传目录存在
        if token_symbol:
            is_image = file_type.upper() == 'IMAGE'
            sub_dir = 'images' if is_image else 'documents'
            upload_folder = os.path.join(
                current_app.static_folder, 
                'uploads', 
                'projects',
                token_symbol,
                sub_dir
            )
            # 确保目录存在
            try:
                os.makedirs(upload_folder, exist_ok=True)
                current_app.logger.info(f'确保上传目录存在: {upload_folder}')
            except Exception as e:
                current_app.logger.error(f'创建上传目录失败: {str(e)}')
                return jsonify({'success': False, 'message': f'服务器错误: 无法创建上传目录: {str(e)}'}), 500
                
            # 检查目录权限
            if not os.access(upload_folder, os.W_OK):
                current_app.logger.error(f'上传目录没有写入权限: {upload_folder}')
                return jsonify({'success': False, 'message': '服务器错误: 上传目录没有写入权限'}), 500
                
        # 保存文件
        try:
            file_urls = save_files([file], asset_type, asset_id, token_symbol)
            
            if not file_urls:
                current_app.logger.error('文件上传保存失败')
                return jsonify({'success': False, 'message': '文件上传保存失败'}), 500
                
            current_app.logger.info(f'文件上传成功: {file_urls}')
            return jsonify({
                'success': True,
                'urls': file_urls
            })
        except ValueError as ve:
            current_app.logger.error(f'文件保存出错 (ValueError): {str(ve)}')
            return jsonify({'success': False, 'message': f'文件保存失败: {str(ve)}'}), 400
        except Exception as se:
            current_app.logger.error(f'文件保存出错 (Exception): {str(se)}')
            return jsonify({'success': False, 'message': f'文件保存失败: {str(se)}'}), 500
            
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        current_app.logger.error(f'上传文件处理失败:\n{error_detail}')
        return jsonify({'success': False, 'message': f'上传处理失败: {str(e)}'}), 500

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

# 添加基于token_symbol的资产所有者检查API
@assets_api_bp.route('/<string:token_symbol>/check_owner')
@eth_address_required
def check_asset_owner_by_symbol(token_symbol):
    """基于token_symbol检查用户是否是资产所有者或管理员"""
    try:
        # 获取资产信息
        asset = Asset.query.filter_by(token_symbol=token_symbol).first_or_404()
        
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
        if owner_address and user_address:
            if owner_address.startswith('0x') and user_address.startswith('0x'):
                # ETH地址比较时都转为小写
                is_owner = user_address.lower() == owner_address.lower()
            else:
                # SOL地址或其他类型地址直接比较（大小写敏感）
                is_owner = user_address == owner_address
        else:
            is_owner = False
        
        return jsonify({
            'is_owner': is_owner,
            'is_admin': is_admin_user
        }), 200
    except Exception as e:
        current_app.logger.error(f'基于token_symbol检查资产所有权失败: {str(e)}')
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
            flash('您没有权限管理此资产的分红', 'warning')
            return redirect(url_for('assets.asset_detail_by_symbol', token_symbol=token_symbol))
        
        # 计算剩余供应量
        if asset.remaining_supply is not None:
            # 优先使用数据库存储的剩余供应量
            remaining_supply = asset.remaining_supply
        else:
            # 如果没有剩余供应量数据，使用总供应量
            remaining_supply = asset.token_supply
        
        current_app.logger.info(f'资产 {asset.id} 分红页面 剩余供应量: {remaining_supply}')
        
        # 渲染分红页面
        return render_template('assets/dividend.html', 
                              asset=asset, 
                              remaining_supply=remaining_supply,
                              can_manage=True)
                              
    except Exception as e:
        current_app.logger.warning(f"访问资产分红页面失败: {str(e)}", exc_info=True)
        flash('访问资产分红页面失败', 'warning')
        return redirect(url_for('assets.list_assets_page'))

@assets_api_bp.route('/check_token_symbol')
def check_token_symbol():
    """检查代币符号是否可用"""
    symbol = request.args.get('symbol')
    
    if not symbol:
        return jsonify({'error': 'Symbol is required'}), 400
    
    # 验证符号格式：必须以RH-开头，后面跟10或20，然后是4位数字
    if not re.match(r'^RH-(10|20)\d{4}$', symbol):
        return jsonify({'error': 'Invalid symbol format', 'available': False}), 400
    
    # 检查数据库中是否已存在该符号
    existing_asset = Asset.query.filter_by(token_symbol=symbol).first()
    
    return jsonify({
        'available': existing_asset is None,
        'exists': existing_asset is not None
    })

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
    
    @app.before_request
    def set_language():
        """设置当前语言"""
        # 从cookie获取语言设置，默认为英文
        lang = request.cookies.get('language', 'en')
        # 确保只支持英文和繁体中文
        if lang not in ['en', 'zh_Hant']:
            lang = 'en'
        # 设置全局语言变量，供模板使用
        g.locale = lang
        current_app.logger.debug(f'当前语言设置为: {lang}')

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

@assets_bp.route('/<asset_id>/qrcode')
def get_asset_qrcode(asset_id):
    try:
        asset = Asset.query.get(asset_id)
        if not asset:
            current_app.logger.warning(f"请求不存在的资产二维码: {asset_id}")
            return jsonify({'success': False, 'message': '资产不存在'}), 404
        
        # 生成资产详情页的URL
        asset_url = url_for('assets.asset_detail', asset_id=asset_id, _external=True)
        
        # 生成二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(asset_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 将图像转换为BytesIO对象
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return send_file(buffer, mimetype='image/png')
    except Exception as e:
        current_app.logger.warning(f"生成资产二维码失败: {str(e)}")
        return jsonify({'success': False, 'message': f'生成二维码失败: {str(e)}'}), 500

@assets_api_bp.route('/create', methods=['POST'])
@eth_address_required
def create_asset_api():
    """创建资产API"""
    try:
        # 获取请求数据
        data = request.json
        if not data:
            current_app.logger.error("资产创建API：请求数据为空")
            return jsonify({
                'success': False,
                'error': '请求数据为空'
            }), 400
            
        # 记录请求数据
        current_app.logger.info(f"资产创建API：收到请求数据 {data}")
        
        # 获取创建者地址
        creator_address = g.eth_address
        if not creator_address:
            current_app.logger.error("资产创建API：未提供创建者地址")
            return jsonify({
                'success': False,
                'error': '未提供创建者地址'
            }), 400
            
        # 验证必填字段
        required_fields = ['name', 'asset_type', 'token_symbol', 'token_supply', 'token_price']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            current_app.logger.error(f"资产创建API：缺少必填字段 {missing_fields}")
            return jsonify({
                'success': False,
                'error': f'缺少必填字段: {", ".join(missing_fields)}'
            }), 400
            
        # 验证代币符号格式和可用性
        token_symbol = data.get('token_symbol')
        if not re.match(r'^RH-(10|20)\d{4}$', token_symbol):
            current_app.logger.error(f"资产创建API：代币符号格式无效 {token_symbol}")
            return jsonify({
                'success': False,
                'error': '无效的代币符号格式'
            }), 400
            
        # 检查代币符号是否已存在
        existing_asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if existing_asset:
            current_app.logger.error(f"资产创建API：代币符号已存在 {token_symbol}")
            return jsonify({
                'success': False,
                'error': f'代币符号 {token_symbol} 已被使用'
            }), 400
            
        # 创建资产记录
        try:
            # 处理图片和文档
            images = data.get('images', [])
            documents = data.get('documents', [])
            
            # 创建资产实例
            new_asset = Asset(
                name=data.get('name'),
                description=data.get('description', ''),
                asset_type=data.get('asset_type'),
                location=data.get('location', ''),
                token_symbol=token_symbol,
                token_supply=data.get('token_supply'),
                token_price=data.get('token_price'),
                remaining_supply=data.get('token_supply'),  # 初始剩余供应量等于总供应量
                total_value=data.get('total_value'),  # 添加 total_value 字段
                area=data.get('area'),  # 添加 area 字段（不动产需要）
                images=json.dumps(images) if images else None,
                documents=json.dumps(documents) if documents else None,
                annual_revenue=data.get('annual_revenue', 1),
                status=1,  # 默认状态：待审核
                creator_address=creator_address,
                owner_address=creator_address,
                payment_tx_hash=data.get('payment_tx_hash'),
                created_at=datetime.now()
            )
            
            # 保存到数据库
            db.session.add(new_asset)
            db.session.commit()
            
            current_app.logger.info(f"资产创建API：成功创建资产 {new_asset.id}, {token_symbol}")
            
            # 添加: 触发支付确认监控任务
            if new_asset.payment_tx_hash:
                try:
                    from app.tasks import monitor_creation_payment_task
                    current_app.logger.info(f"触发支付确认监控任务: AssetID={new_asset.id}, TxHash={new_asset.payment_tx_hash}")
                    # 使用DelayedTask的delay方法触发任务
                    monitor_creation_payment_task.delay(new_asset.id, new_asset.payment_tx_hash)
                    current_app.logger.info(f"支付确认监控任务已在新线程中启动: AssetID={new_asset.id}")
                    
                    # 更新支付详情
                    payment_details = {
                        'tx_hash': new_asset.payment_tx_hash,
                        'timestamp': datetime.now().isoformat(),
                        'status': 'pending'
                    }
                    new_asset.payment_details = json.dumps(payment_details)
                    db.session.commit()
                    current_app.logger.info(f"更新资产支付详情: AssetID={new_asset.id}")
                except Exception as task_error:
                    current_app.logger.error(f"触发支付确认监控任务失败: {str(task_error)}")
                    # 记录详细的错误堆栈
                    import traceback
                    current_app.logger.error(traceback.format_exc())
            
            # 返回成功响应
            return jsonify({
                'success': True,
                'message': '资产创建成功',
                'id': new_asset.id,
                'token_symbol': token_symbol
            }), 201
            
        except Exception as db_error:
            db.session.rollback()
            current_app.logger.error(f"资产创建API：数据库操作失败 {str(db_error)}")
            return jsonify({
                'success': False,
                'error': f'数据库操作失败: {str(db_error)}'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"资产创建API：处理请求失败 {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'处理请求失败: {str(e)}'
        }), 500
