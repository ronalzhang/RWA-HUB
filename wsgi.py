import os
from app import create_app
from waitress import serve

# 创建应用实例
flask_app = create_app(os.getenv('FLASK_ENV', 'production'))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 9000))
    host = '0.0.0.0'  # 允许外部访问
    
    # 使用waitress作为生产服务器
    serve(flask_app, 
          host=host, 
          port=port, 
          threads=8,           # 增加线程数
          url_scheme='http',   # 修改为http
          channel_timeout=300, # 增加超时时间
          cleanup_interval=30, # 清理间隔
          max_request_body_size=1073741824  # 最大请求体大小（1GB）
    )