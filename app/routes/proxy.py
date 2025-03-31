import os
import time
import requests
import mimetypes
from flask import current_app, send_file, abort, make_response, Response
from . import proxy_bp
from urllib.parse import urlparse

# 缓存目录
CACHE_DIR = os.path.join(os.getcwd(), 'app/static/vendor')

# 确保缓存目录存在
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# 缓存URL映射，将外部URL映射到本地文件
VENDOR_MAPPING = {
    # Solana相关库
    'solana-web3.js': 'https://unpkg.com/@solana/web3.js@latest/lib/index.iife.min.js',
    'solana-web3-stable.js': 'https://unpkg.com/@solana/web3.js@1.98.0/lib/index.iife.min.js',
    'solana-spl-token.js': 'https://unpkg.com/@solana/spl-token@0.3.8/dist/index.iife.js',
    
    # Web3和区块链相关
    'web3.min.js': 'https://unpkg.com/web3@1.5.2/dist/web3.min.js',
    'ethereumjs-tx-1.3.7.min.js': 'https://cdn.jsdelivr.net/npm/ethereumjs-tx@1.3.7/dist/index.min.js',
    'ethers.umd.min.js': 'https://cdn.ethers.io/lib/ethers-5.2.umd.min.js',
    
    # 基础库
    'jquery.min.js': 'https://code.jquery.com/jquery-3.6.0.min.js',
    'jquery-ui.min.js': 'https://code.jquery.com/ui/1.13.2/jquery-ui.min.js',
    'jquery-ui.min.css': 'https://code.jquery.com/ui/1.13.2/themes/base/jquery-ui.min.css',
    
    # Bootstrap
    'bootstrap.min.css': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'bootstrap.bundle.min.js': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
    
    # Font Awesome
    'all.min.css': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
    
    # Animations
    'aos.css': 'https://unpkg.com/aos@2.3.1/dist/aos.css',
    'aos.js': 'https://unpkg.com/aos@2.3.1/dist/aos.js',
    'animate.min.css': 'https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css',
    
    # 图表库
    'chart.min.js': 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js',
    
    # 工具库
    'moment.min.js': 'https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.4/moment.min.js',
    'lodash.min.js': 'https://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.17.21/lodash.min.js',
    'axios.min.js': 'https://cdn.jsdelivr.net/npm/axios@1.6.2/dist/axios.min.js',
    
    # 数据表格
    'datatables.min.js': 'https://cdn.datatables.net/1.13.7/js/jquery.dataTables.min.js',
    'datatables.min.css': 'https://cdn.datatables.net/1.13.7/css/jquery.dataTables.min.css',
    
    # 表单验证
    'validate.min.js': 'https://cdn.jsdelivr.net/npm/jquery-validation@1.19.5/dist/jquery.validate.min.js',
}

@proxy_bp.route('/external/<path:url>', methods=['GET'])
def proxy_external(url):
    """代理外部URL的内容"""
    try:
        current_app.logger.info(f"代理外部URL: {url}")
        
        # 检查安全性 - 防止恶意URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            current_app.logger.error(f"无效的URL格式: {url}")
            abort(400)
        
        # 发送请求获取资源
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            current_app.logger.error(f"获取外部资源失败: {url}, 状态码: {response.status_code}")
            abort(response.status_code)
        
        # 处理内容类型
        content_type = response.headers.get('Content-Type', 'application/octet-stream')
        
        # 创建响应
        resp = make_response(response.content)
        resp.headers['Content-Type'] = content_type
        resp.headers['Cache-Control'] = 'public, max-age=86400'  # 缓存1天
        
        current_app.logger.info(f"成功代理外部资源: {url}")
        return resp
        
    except Exception as e:
        current_app.logger.error(f"代理外部资源出错: {str(e)}")
        abort(500)

@proxy_bp.route('/cached_vendor/<filename>', methods=['GET'])
def cached_vendor(filename):
    """提供缓存的第三方库文件"""
    try:
        current_app.logger.info(f"请求缓存的供应商文件: {filename}")
        
        # 检查文件是否在映射中
        if filename not in VENDOR_MAPPING:
            current_app.logger.error(f"未知的供应商文件: {filename}")
            abort(404)
        
        filepath = os.path.join(CACHE_DIR, filename)
        external_url = VENDOR_MAPPING[filename]
        
        # 检查文件是否已缓存且未过期（24小时）
        is_cached = os.path.exists(filepath)
        is_expired = False
        
        if is_cached:
            # 检查文件是否过期（超过24小时）
            file_time = os.path.getmtime(filepath)
            current_time = time.time()
            is_expired = (current_time - file_time) > 86400  # 24小时 = 86400秒
        
        # 如果文件不存在或已过期，下载它
        if not is_cached or is_expired:
            current_app.logger.info(f"下载供应商文件: {filename} 从 {external_url}")
            
            try:
                response = requests.get(external_url, timeout=10)
                if response.status_code == 200:
                    # 确保目录存在
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    
                    # 保存文件内容
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    current_app.logger.info(f"成功下载并缓存: {filename}")
                else:
                    current_app.logger.error(f"下载失败 {filename}: {response.status_code}")
                    
                    # 如果文件已经存在，使用现有文件（即使已过期）
                    if not is_cached:
                        abort(response.status_code)
            except Exception as e:
                current_app.logger.error(f"下载 {filename} 时出错: {str(e)}")
                
                # 如果文件已经存在，使用现有文件（即使已过期）
                if not is_cached:
                    abort(500)
        
        # 提供文件
        content_type = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'
        
        # 如果是字体文件，需要特殊处理
        if filename.startswith('webfonts/'):
            font_extensions = {'.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.eot': 'application/vnd.ms-fontobject', '.svg': 'image/svg+xml'}
            for ext, mime in font_extensions.items():
                if filename.endswith(ext):
                    content_type = mime
                    break
        
        current_app.logger.info(f"提供缓存的供应商文件: {filename}, 类型: {content_type}")
        return send_file(filepath, mimetype=content_type, max_age=86400)
        
    except Exception as e:
        current_app.logger.error(f"提供缓存的供应商文件出错: {str(e)}")
        abort(500)

@proxy_bp.route('/webfonts/<filename>', methods=['GET'])
def serve_webfonts(filename):
    """提供字体文件"""
    try:
        filepath = os.path.join(CACHE_DIR, 'webfonts', filename)
        
        # 确保webfonts目录存在
        webfonts_dir = os.path.join(CACHE_DIR, 'webfonts')
        if not os.path.exists(webfonts_dir):
            os.makedirs(webfonts_dir)
        
        # 如果文件不存在，尝试从Font Awesome CDN获取
        if not os.path.exists(filepath):
            fa_url = f'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/{filename}'
            current_app.logger.info(f"下载字体文件: {filename} 从 {fa_url}")
            
            try:
                response = requests.get(fa_url, timeout=10)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    current_app.logger.info(f"成功下载并缓存字体文件: {filename}")
                else:
                    current_app.logger.error(f"下载字体文件失败 {filename}: {response.status_code}")
                    abort(response.status_code)
            except Exception as e:
                current_app.logger.error(f"下载字体文件 {filename} 时出错: {str(e)}")
                abort(500)
        
        # 确定内容类型
        font_extensions = {'.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.eot': 'application/vnd.ms-fontobject', '.svg': 'image/svg+xml'}
        content_type = 'application/octet-stream'
        
        for ext, mime in font_extensions.items():
            if filename.endswith(ext):
                content_type = mime
                break
        
        current_app.logger.info(f"提供字体文件: {filename}, 类型: {content_type}")
        return send_file(filepath, mimetype=content_type)
    except Exception as e:
        current_app.logger.error(f"提供字体文件出错: {str(e)}")
        abort(500) 