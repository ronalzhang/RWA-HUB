import os
from app import create_app

# 创建应用实例
application = create_app(os.getenv('FLASK_ENV', 'production')) 