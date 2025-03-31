from flask import Blueprint, request, Response, send_from_directory
import requests
import os

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
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
            except Exception as e:
                return str(e), 500
    
    # 如果文件存在（或已下载），直接返回
    if os.path.exists(file_path):
        return send_from_directory(vendor_dir, filename)
    else:
        return f"资源 {filename} 不可用", 404 