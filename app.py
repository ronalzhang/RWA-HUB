import logging
import os
from app import create_app
from app.routes.api import api
from app.routes.admin import admin_bp
from app.routes.auth import auth
from app.routes.dashboard import dashboard
from app.routes.solana_api import solana_api

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    # 启动应用
    app.run(host='0.0.0.0', port=5000, debug=True)