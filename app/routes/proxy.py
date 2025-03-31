from flask import Blueprint, request, Response, send_from_directory, jsonify, current_app
import requests
import os
import shutil

proxy_bp = Blueprint('proxy', __name__)

ALLOWED_DOMAINS = {
    'unpkg.com',
    'cdn.jsdelivr.net',
    'cdnjs.cloudflare.com'
}

@proxy_bp.route('/proxy/<path:url>')
def proxy(url):
    try:
        # 解析原始URL的域名
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc

        # 检查域名是否在允许列表中
        if domain not in ALLOWED_DOMAINS:
            return 'Domain not allowed', 403

        # 获取原始请求的查询参数
        params = request.args.to_dict()
        
        # 发送请求到目标URL
        response = requests.get(url, params=params, stream=True)
        
        # 创建响应对象
        proxy_response = Response(
            response.iter_content(chunk_size=1024),
            status=response.status_code
        )
        
        # 复制原始响应的headers
        for key, value in response.headers.items():
            if key.lower() not in ('content-length', 'content-encoding', 'transfer-encoding'):
                proxy_response.headers[key] = value
                
        return proxy_response
        
    except Exception as e:
        return str(e), 500

# 静态资源缓存路由
@proxy_bp.route('/static/vendor/<path:filename>')
def cached_vendor(filename):
    vendor_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'vendor')
    if not os.path.exists(vendor_dir):
        os.makedirs(vendor_dir)
        
    file_path = os.path.join(vendor_dir, filename)
    
    # 如果文件不存在，从CDN下载
    if not os.path.exists(file_path):
        cdn_urls = {
            'solana-web3.min.js': 'https://unpkg.com/@solana/web3.js@1.98.0/lib/index.iife.min.js',
            'web3.min.js': 'https://unpkg.com/web3@1.5.2/dist/web3.min.js',
            'bootstrap.min.css': 'https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css',
            'all.min.css': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
            'aos.css': 'https://cdnjs.cloudflare.com/ajax/libs/aos/2.3.1/aos.css',
            'jquery.min.js': 'https://code.jquery.com/jquery-3.6.0.min.js',
            'bootstrap.bundle.min.js': 'https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/js/bootstrap.bundle.min.js',
            'aos.js': 'https://cdnjs.cloudflare.com/ajax/libs/aos/2.3.1/aos.js'
        }
        
        if filename in cdn_urls:
            try:
                response = requests.get(cdn_urls[filename])
                if response.status_code == 200:
                    content = response.content
                    
                    # 修正 Font Awesome CSS 中的字体路径
                    if filename == 'all.min.css':
                        content = fix_font_awesome_paths(content)
                        # 下载字体文件
                        download_font_awesome_files(vendor_dir)
                        
                    # 保存修正后的内容
                    with open(file_path, 'wb') as f:
                        f.write(content)
            except Exception as e:
                return str(e), 500
    
    # 如果文件存在（或已下载），直接返回
    if os.path.exists(file_path):
        return send_from_directory(vendor_dir, filename)
    else:
        return f"资源 {filename} 不可用", 404

def fix_font_awesome_paths(content):
    """修正 Font Awesome CSS 中的字体文件路径"""
    content_str = content.decode('utf-8')
    
    # 替换字体路径为我们的代理路径
    content_str = content_str.replace('url(../webfonts/', 'url(/proxy/static/webfonts/')
    content_str = content_str.replace('url("../webfonts/', 'url("/proxy/static/webfonts/')
    content_str = content_str.replace("url('../webfonts/", "url('/proxy/static/webfonts/")
    
    return content_str.encode('utf-8')

# 字体文件路由
@proxy_bp.route('/proxy/static/webfonts/<path:filename>')
def webfonts(filename):
    webfonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'vendor', 'webfonts')
    if not os.path.exists(webfonts_dir):
        os.makedirs(webfonts_dir)
        
    file_path = os.path.join(webfonts_dir, filename)
    
    # 如果文件不存在，从CDN下载
    if not os.path.exists(file_path):
        font_urls = {
            'fa-solid-900.woff2': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/webfonts/fa-solid-900.woff2',
            'fa-solid-900.ttf': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/webfonts/fa-solid-900.ttf',
            'fa-regular-400.woff2': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/webfonts/fa-regular-400.woff2',
            'fa-regular-400.ttf': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/webfonts/fa-regular-400.ttf',
            'fa-brands-400.woff2': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/webfonts/fa-brands-400.woff2',
            'fa-brands-400.ttf': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/webfonts/fa-brands-400.ttf'
        }
        
        if filename in font_urls:
            try:
                response = requests.get(font_urls[filename])
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
            except Exception as e:
                return str(e), 500
    
    # 如果文件存在（或已下载），直接返回
    if os.path.exists(file_path):
        return send_from_directory(webfonts_dir, filename)
    else:
        return f"字体文件 {filename} 不可用", 404

def download_font_awesome_files(vendor_dir):
    """下载 Font Awesome 字体文件"""
    webfonts_dir = os.path.join(vendor_dir, 'webfonts')
    if not os.path.exists(webfonts_dir):
        os.makedirs(webfonts_dir)
    
    font_files = [
        'fa-solid-900.woff2',
        'fa-solid-900.ttf',
        'fa-regular-400.woff2',
        'fa-regular-400.ttf',
        'fa-brands-400.woff2',
        'fa-brands-400.ttf'
    ]
    
    for font_file in font_files:
        url = f'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/webfonts/{font_file}'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(os.path.join(webfonts_dir, font_file), 'wb') as f:
                    f.write(response.content)
        except Exception as e:
            print(f"下载字体文件 {font_file} 失败: {str(e)}")

@proxy_bp.route('/api/user/assets', methods=['GET'])
def proxy_user_assets():
    """获取用户资产"""
    try:
        address = request.args.get('address')
        wallet_type = request.args.get('wallet_type', 'ethereum')
        
        # 硬编码三个测试资产
        test_assets = [
            {
                "asset_id": 1,
                "id": 1,
                "name": "Palm Jumeirah Luxury Villa 8101",
                "token_symbol": "RH-108235",
                "price": 1.5,
                "token_price": 1.5,
                "holding_amount": 100
            },
            {
                "asset_id": 2,
                "id": 2,
                "name": "Chinook Regional Hospital",
                "token_symbol": "RH-205020",
                "price": 2.75,
                "token_price": 2.75,
                "holding_amount": 50
            },
            {
                "asset_id": 4,
                "id": 4,
                "name": "BTC ETF",
                "token_symbol": "RH-205447",
                "price": 0.85,
                "token_price": 0.85,
                "holding_amount": 200
            }
        ]
        
        # 返回JSON格式的测试资产数据
        return jsonify(test_assets)
    except Exception as e:
        current_app.logger.error(f"获取用户资产失败: {str(e)}")
        return jsonify([]) 