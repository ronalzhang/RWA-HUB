from flask import render_template, send_from_directory, current_app, abort, request, redirect, url_for, jsonify, g
from . import assets_bp, assets_api_bp
from .. import db  # 直接从应用实例导入 db
from ..models import Asset
from ..models.asset import AssetStatus
from ..utils import is_admin, save_files
from ..utils.decorators import eth_address_required
from ..utils.storage import storage
import os
import json
from datetime import datetime
import random

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

@assets_bp.route("/<int:asset_id>/edit", methods=['PUT'])
@eth_address_required
def edit_asset(asset_id):
    """编辑资产"""
    try:
        # 获取资产信息
        asset = Asset.query.get_or_404(asset_id)
        
        # 检查权限
        if not is_admin(g.eth_address) and asset.owner_address != g.eth_address:
            return jsonify({'error': '没有编辑权限'}), 403
            
        # 如果资产已上链，不允许编辑
        if asset.token_address:
            return jsonify({'error': '已上链资产不可修改'}), 400
            
        # 更新基本信息
        asset.name = request.form.get('name', asset.name)
        asset.description = request.form.get('description', asset.description)
        asset.location = request.form.get('location', asset.location)
        asset.area = float(request.form.get('area')) if request.form.get('area') else asset.area
        asset.total_value = float(request.form.get('total_value')) if request.form.get('total_value') else asset.total_value
        asset.annual_revenue = float(request.form.get('annual_revenue')) if request.form.get('annual_revenue') else asset.annual_revenue
        
        # 处理图片文件
        if 'images[]' in request.files:
            images = request.files.getlist('images[]')
            if images and any(image.filename for image in images):
                image_paths = []
                asset_type_folder = 'real_estate' if asset.asset_type == '10' else 'quasi_real_estate'
                
                # 删除旧图片
                if asset.images:
                    old_images = json.loads(asset.images)
                    for old_image in old_images:
                        try:
                            # 从URL中提取key
                            key = old_image.split('/')[-1]
                            storage.delete(f'{asset_type_folder}/{asset.id}/{key}')
                        except Exception as e:
                            current_app.logger.error(f'删除旧图片失败: {str(e)}')
                
                # 上传新图片
                for i, image in enumerate(images):
                    if image and image.filename and allowed_file(image.filename, ['jpg', 'jpeg', 'png']):
                        try:
                            # 构建文件名
                            ext = image.filename.rsplit(".", 1)[1].lower()
                            filename = f'{asset_type_folder}/{asset.id}/image_{i+1}.{ext}'
                            
                            # 读取文件内容
                            file_data = image.read()
                            
                            # 检查七牛云存储是否初始化
                            if storage is None:
                                current_app.logger.error('七牛云存储未初始化')
                                raise Exception("七牛云存储未初始化")
                                
                            # 上传到七牛云
                            current_app.logger.info(f'开始上传图片到七牛云: {filename}')
                            url = storage.upload(file_data, filename)
                            
                            if url:
                                # 确保URL不包含@符号
                                if url.startswith('@'):
                                    url = url[1:]
                                image_paths.append(url)
                                current_app.logger.info(f'图片上传成功: {url}')
                            else:
                                current_app.logger.error(f'七牛云返回的URL为空: {filename}')
                                raise Exception("七牛云上传失败")
                                
                        except Exception as e:
                            current_app.logger.error(f'上传图片失败: {str(e)}')
                            current_app.logger.error(f'文件名: {image.filename}, 目标路径: {filename}')
                            continue
                
                if image_paths:
                    asset.images = json.dumps(image_paths)
                    
        # 处理文档文件
        if 'documents[]' in request.files:
            documents = request.files.getlist('documents[]')
            if documents and any(doc.filename for doc in documents):
                doc_paths = []
                asset_type_folder = 'real_estate' if asset.asset_type == '10' else 'quasi_real_estate'
                
                # 删除旧文档
                if asset.documents:
                    old_docs = json.loads(asset.documents)
                    for old_doc in old_docs:
                        try:
                            # 从URL中提取key
                            key = old_doc.split('/')[-1]
                            storage.delete(f'{asset_type_folder}/{asset.id}/documents/{key}')
                        except Exception as e:
                            current_app.logger.error(f'删除旧文档失败: {str(e)}')
                
                # 上传新文档
                for i, doc in enumerate(documents):
                    if doc and doc.filename and allowed_file(doc.filename, ['pdf', 'doc', 'docx']):
                        try:
                            # 构建文件名
                            ext = doc.filename.rsplit(".", 1)[1].lower()
                            filename = f'{asset_type_folder}/{asset.id}/documents/document_{i+1}.{ext}'
                            
                            # 读取文件内容
                            file_data = doc.read()
                            
                            # 上传到七牛云
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
        return jsonify({'message': '更新成功'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'更新资产失败: {str(e)}', exc_info=True)
        return jsonify({'error': '更新资产失败'}), 500

# @assets_bp.route("/static/uploads/<path:filename>")
# def serve_uploaded_file(filename):
#     """提供上传文件的访问（已弃用，改用七牛云）"""
#     pass  # 注释掉整个函数体

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
        # 记录请求信息
        current_app.logger.info('开始处理创建资产请求')
        current_app.logger.info(f'请求方法: {request.method}')
        current_app.logger.info(f'请求头: {dict(request.headers)}')
        current_app.logger.info(f'表单数据: {dict(request.form)}')
        current_app.logger.info(f'文件: {dict(request.files)}')
        
        # 获取表单数据
        name = request.form.get('name')
        asset_type = int(request.form.get('asset_type'))  # 转换为整数
        total_value = request.form.get('total_value')
        annual_revenue = request.form.get('annual_revenue')
        description = request.form.get('description')
        location = request.form.get('location')
        area = request.form.get('area')
        token_supply = request.form.get('token_supply')
        token_price = request.form.get('token_price')
        
        # 生成代币符号
        while True:
            random_num = ''.join([str(random.randint(0, 9)) for _ in range(4)])
            token_symbol = f"RH-{asset_type}{random_num}"
            
            # 检查代币符号是否已存在
            existing_asset = Asset.query.filter_by(token_symbol=token_symbol).first()
            if not existing_asset:
                break
            
        # 记录获取到的字段值
        current_app.logger.info('获取到的字段值:')
        current_app.logger.info(f'name: {name}')
        current_app.logger.info(f'asset_type: {asset_type}')
        current_app.logger.info(f'total_value: {total_value}')
        current_app.logger.info(f'annual_revenue: {annual_revenue}')
        current_app.logger.info(f'description: {description}')
        current_app.logger.info(f'location: {location}')
        current_app.logger.info(f'area: {area}')
        current_app.logger.info(f'token_supply: {token_supply}')
        current_app.logger.info(f'token_price: {token_price}')
        
        # 验证必填字段
        required_fields = {
            'name': name,
            'asset_type': asset_type,
            'total_value': total_value,
            'annual_revenue': annual_revenue,
            'description': description,
            'location': location
        }
        
        # 根据资产类型添加额外的必填字段
        if asset_type == 20:  # 类不动产
            current_app.logger.info('资产类型为类不动产，添加 token_supply 必填字段')
            required_fields['token_supply'] = token_supply
        elif asset_type == 10:  # 不动产
            current_app.logger.info('资产类型为不动产，添加 area 必填字段')
            required_fields['area'] = area
            
        # 检查必填字段
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            current_app.logger.warning(f'缺少必填字段: {missing_fields}')
            current_app.logger.warning('必填字段验证失败，返回400错误')
            return jsonify({
                'error': f'缺少必填字段: {", ".join(missing_fields)}',
                'missing_fields': missing_fields,
                'received_values': {k: v for k, v in required_fields.items()}
            }), 400
            
        # 检查图片文件
        images = request.files.getlist('images[]')
        if not images or not any(image.filename for image in images):
            current_app.logger.warning('未上传图片文件')
            return jsonify({'error': '请至少上传一张资产图片'}), 400
            
        # 创建资产记录
        try:
            current_app.logger.info('开始创建资产记录')
            current_app.logger.info(f'创建资产参数: name={name}, asset_type={asset_type}, token_symbol={token_symbol}, total_value={total_value}')
            
            asset = Asset(
                name=name,
                asset_type=asset_type,
                total_value=float(total_value),
                token_symbol=token_symbol,
                token_price=float(token_price) if token_price else 0,
                token_supply=int(token_supply) if token_supply else None,
                annual_revenue=float(annual_revenue),
                description=description,
                location=location,
                area=float(area) if area else None,
                owner_address=g.eth_address,
                creator_address=g.eth_address,  # 设置创建者地址
                status=AssetStatus.PENDING.value  # 使用枚举值
            )
            
            # 先添加资产记录并获取ID
            current_app.logger.info('添加资产记录到数据库')
            db.session.add(asset)
            db.session.flush()
            current_app.logger.info(f'资产记录创建成功，ID: {asset.id}')
            
            # 处理图片文件
            image_paths = []
            asset_type_folder = 'real_estate' if asset_type == 10 else 'quasi_real_estate'
            
            current_app.logger.info(f'开始处理图片上传，资产类型文件夹: {asset_type_folder}')
            
            for i, image in enumerate(images):
                if image and image.filename and allowed_file(image.filename, ['jpg', 'jpeg', 'png']):
                    try:
                        # 构建文件名
                        ext = image.filename.rsplit(".", 1)[1].lower()
                        filename = f'{asset_type_folder}/{asset.id}/image_{i+1}.{ext}'
                        
                        current_app.logger.info(f'处理第 {i+1} 张图片: {image.filename} -> {filename}')
                        
                        # 读取文件内容
                        file_data = image.read()
                        
                        # 检查七牛云存储是否初始化
                        if storage is None:
                            current_app.logger.error('七牛云存储未初始化')
                            raise Exception("七牛云存储未初始化")
                        
                        # 上传到七牛云
                        current_app.logger.info(f'开始上传图片到七牛云: {filename}')
                        url = storage.upload(file_data, filename)
                        
                        if url:
                            # 确保URL不包含@符号
                            if url.startswith('@'):
                                url = url[1:]
                            image_paths.append(url)
                            current_app.logger.info(f'图片上传成功: {url}')
                        else:
                            current_app.logger.error(f'七牛云返回的URL为空: {filename}')
                            raise Exception("七牛云上传失败")
                            
                    except Exception as e:
                        current_app.logger.error(f'上传图片失败: {str(e)}')
                        current_app.logger.error(f'文件名: {image.filename}, 目标路径: {filename}')
                        continue
                else:
                    current_app.logger.warning(f'跳过无效的图片文件: {image.filename if image else "None"}')
            
            # 保存图片路径到资产记录
            if not image_paths:
                current_app.logger.error('没有成功上传任何图片')
                raise Exception('没有成功保存任何图片')
                
            current_app.logger.info(f'所有图片上传成功，保存路径列表: {image_paths}')
            asset.images = json.dumps(image_paths)
            
            # 处理文档文件
            documents = request.files.getlist('documents[]')
            if documents:
                doc_paths = []
                for i, doc in enumerate(documents):
                    if doc and doc.filename and allowed_file(doc.filename, ['pdf', 'doc', 'docx']):
                        try:
                            # 构建文件名
                            ext = doc.filename.rsplit(".", 1)[1].lower()
                            filename = f'{asset_type_folder}/{asset.id}/documents/document_{i+1}.{ext}'
                            
                            # 读取文件内容
                            file_data = doc.read()
                            
                            # 上传到七牛云
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
            
            # 提交所有更改
            db.session.commit()
            current_app.logger.info(f'创建资产成功: id={asset.id}, 图片={image_paths}')
            
            return jsonify({
                'message': '创建资产成功',
                'id': asset.id
            }), 201
            
        except Exception as e:
            current_app.logger.error(f'创建资产记录失败: {str(e)}', exc_info=True)
            db.session.rollback()
            return jsonify({'error': f'创建资产失败: {str(e)}'}), 500
            
    except Exception as e:
        current_app.logger.error(f'创建资产失败: {str(e)}', exc_info=True)
        return jsonify({'error': '创建资产失败'}), 500

def allowed_file(filename, allowed_extensions):
    """检查文件类型是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
