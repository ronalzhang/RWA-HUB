import os
import sys
from waitress import serve
from flask import Flask

# 更新Python路径
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# 创建Flask应用
def create_flask_app():
    # 导入应用配置和扩展
    from app.config import config
    from app.extensions import db, babel, limiter, scheduler, migrate, cors, configure_logging
    
    # 创建Flask应用实例，指定正确的模板和静态目录
    app = Flask(
        __name__,
        template_folder='app/templates',
        static_folder='app/static',
        static_url_path='/static'
    )
    
    # 加载配置
    config_name = os.getenv('FLASK_ENV', 'production')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 初始化日志
    configure_logging(app)
    
    # 初始化扩展
    db.init_app(app)
    babel.init_app(app)
    limiter.init_app(app)
    cors.init_app(app)
    migrate.init_app(app, db)
    
    # 注册蓝图
    with app.app_context():
        # 注册蓝图和路由
        from app.routes import register_blueprints
        register_blueprints(app)
        
        # 注册管理员API v2蓝图
        from app.routes.admin_api import register_admin_v2_blueprint
        register_admin_v2_blueprint(app)
    
    return app

# 创建应用实例
flask_app = create_flask_app()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 9000))
    serve(flask_app, host='0.0.0.0', port=port) 