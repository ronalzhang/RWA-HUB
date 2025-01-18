from flask import render_template, send_from_directory, current_app, abort, request, redirect, url_for, jsonify, g
from . import assets_bp, assets_api_bp
from ..models import db, Asset
from ..models.asset import AssetStatus
from ..utils import is_admin, save_files
from ..utils.decorators import eth_address_required
import os
import json

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
    """资产详情页面"""
    try:
        # 获取资产信息
        asset = Asset.query.get_or_404(asset_id)
        
        # 获取分红历史
        dividend_records = asset.dividend_records if asset.dividend_records else []
        
        # 获取当前用户的钱包地址
        eth_address = request.headers.get('X-Eth-Address') or request.cookies.get('eth_address')
        
        # 计算剩余可售数量（如果已上链则从合约获取，否则等于发行总量）
        remaining_supply = asset.token_supply
        if asset.token_address:
            # TODO: 从合约获取实际剩余数量
            pass
            
        return render_template("assets/detail.html", 
                             asset=asset,
                             dividend_records=dividend_records,
                             remaining_supply=remaining_supply,
                             current_user_address=eth_address,
                             is_admin=is_admin(eth_address))
    except Exception as e:
        current_app.logger.error(f"获取资产详情失败: {str(e)}")
        abort(404)

@assets_bp.route("/create")
def create_asset_page():
    """创建资产页面"""
    eth_address = request.headers.get('X-Eth-Address') or request.cookies.get('eth_address')
    if not eth_address:
        return redirect(url_for('main.index'))
    return render_template("assets/create.html")

@assets_bp.route("/<int:asset_id>/edit")
def edit_asset_page(asset_id):
    """编辑资产页面"""
    # 从请求参数获取钱包地址和上链状态
    eth_address = request.headers.get('X-Eth-Address') or request.cookies.get('eth_address')
    if not eth_address:
        return redirect(url_for('main.index'))
    
    # 检查管理员权限
    if not is_admin(eth_address):
        return redirect(url_for('main.index'))
        
    # 获取资产信息
    asset = Asset.query.get_or_404(asset_id)
    
    # 如果资产已上链，重定向到首页
    if asset.token_address:
        return redirect(url_for('main.index'))
        
    return render_template('assets/edit.html', asset_id=asset_id)

@assets_bp.route("/static/uploads/<path:filename>")
def serve_uploaded_file(filename):
    """提供上传文件的访问"""
    try:
        # 获取上传目录
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        current_app.logger.info(f"上传目录: {uploads_dir}")
        
        # 构建完整的文件路径
        file_path = os.path.join(uploads_dir, filename)
        current_app.logger.info(f"请求的文件路径: {file_path}")
        
        # 检查文件是否存在
        if os.path.exists(file_path):
            current_app.logger.info(f"文件存在，准备发送: {file_path}")
            return send_from_directory(uploads_dir, filename)
            
        current_app.logger.error(f"文件不存在: {file_path}")
        abort(404)
    except Exception as e:
        current_app.logger.error(f"处理文件访问时出错 {filename}: {str(e)}")
        abort(404)

@assets_bp.route('/<int:asset_id>/dividend')
def dividend_page(asset_id):
    """资产分红管理页面"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        return render_template('assets/dividend.html', asset=asset)
    except Exception as e:
        current_app.logger.error(f'访问分红管理页面失败: {str(e)}')
        flash('访问分红管理页面失败')
        return redirect(url_for('assets.list'))

@assets_api_bp.route('', methods=['POST'])
@eth_address_required
def create_asset():
    """创建资产"""
    try:
        # 获取表单数据
        name = request.form.get('name')
        asset_type = request.form.get('asset_type')
        total_value = request.form.get('total_value')
        token_code = request.form.get('token_code')
        annual_revenue = request.form.get('annual_revenue')
        description = request.form.get('description')
        location = request.form.get('location')
        area = request.form.get('area')
        
        # 验证必填字段
        if not all([name, asset_type, total_value, token_code, annual_revenue]):
            return jsonify({'error': '缺少必填字段'}), 400
            
        # 检查图片文件
        images = request.files.getlist('images[]')
        if not images or not any(image.filename for image in images):
            return jsonify({'error': '请至少上传一张资产图片'}), 400
            
        # 创建资产记录
        asset = Asset(
            name=name,
            asset_type=asset_type,
            total_value=float(total_value),
            token_code=token_code,
            annual_revenue=float(annual_revenue),
            description=description,
            location=location,
            area=float(area) if area else None,
            owner_address=g.eth_address,
            status=AssetStatus.PENDING
        )
        
        try:
            # 先添加资产记录并获取ID
            db.session.add(asset)
            db.session.flush()
            
            # 处理图片文件
            image_paths = []
            asset_type_folder = 'real_estate' if asset_type == '10' else 'quasi_real_estate'
            
            for i, image in enumerate(images):
                if image and image.filename and allowed_file(image.filename, ['jpg', 'jpeg', 'png']):
                    try:
                        # 构建保存路径
                        save_dir = os.path.join(current_app.root_path, 'static', 'uploads', asset_type_folder, str(asset.id))
                        os.makedirs(save_dir, exist_ok=True)
                        
                        # 保存文件
                        filename = f'image_{i+1}.{image.filename.rsplit(".", 1)[1].lower()}'
                        file_path = os.path.join(save_dir, filename)
                        image.save(file_path)
                        
                        # 记录相对路径 - 从 app/static/uploads 开始计算相对路径
                        relative_path = os.path.join(asset_type_folder, str(asset.id), filename)
                        image_paths.append(relative_path)
                        current_app.logger.info(f'保存图片成功: {file_path}, 相对路径: {relative_path}')
                    except Exception as e:
                        current_app.logger.error(f'保存图片失败: {str(e)}')
                        continue
            
            # 保存图片路径到资产记录
            if not image_paths:
                raise Exception('没有成功保存任何图片')
            asset.images = json.dumps(image_paths)
            
            # 处理文档文件
            documents = request.files.getlist('documents[]')
            if documents:
                doc_paths = []
                for i, doc in enumerate(documents):
                    if doc and doc.filename and allowed_file(doc.filename, ['pdf', 'doc', 'docx']):
                        try:
                            # 构建保存路径
                            save_dir = os.path.join(current_app.root_path, 'static', 'uploads', asset_type_folder, str(asset.id), 'documents')
                            os.makedirs(save_dir, exist_ok=True)
                            
                            # 保存文件
                            filename = f'document_{i+1}.{doc.filename.rsplit(".", 1)[1].lower()}'
                            file_path = os.path.join(save_dir, filename)
                            doc.save(file_path)
                            
                            # 记录相对路径 - 从 app/static/uploads 开始计算相对路径
                            relative_path = os.path.join(asset_type_folder, str(asset.id), 'documents', filename)
                            doc_paths.append(relative_path)
                            current_app.logger.info(f'保存文档成功: {file_path}, 相对路径: {relative_path}')
                        except Exception as e:
                            current_app.logger.error(f'保存文档失败: {str(e)}')
                            continue
                
                if doc_paths:
                    asset.documents = json.dumps(doc_paths)
            
            # 提交所有更改
            db.session.commit()
            current_app.logger.info(f'创建资产成功: id={asset.id}, 图片={image_paths}')
            
            return jsonify({
                'message': '创建资产成功',
                'id': asset.id
            }), 201
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'保存资产记录失败: {str(e)}', exc_info=True)
            return jsonify({'error': '保存资产记录失败'}), 500
            
    except Exception as e:
        current_app.logger.error(f'创建资产失败: {str(e)}', exc_info=True)
        return jsonify({'error': '创建资产失败'}), 500

def allowed_file(filename, allowed_extensions):
    """检查文件类型是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
