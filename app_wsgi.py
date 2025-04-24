import os
import sys
from waitress import serve
from flask import Flask
from decimal import Decimal

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
    
    # 添加Solana配置
    app.config['SOLANA_ENDPOINT'] = os.getenv('SOLANA_ENDPOINT', 'https://api.mainnet-beta.solana.com')
    
    # 初始化日志
    configure_logging(app)
    
    # 初始化扩展
    db.init_app(app)
    babel.init_app(app)
    limiter.init_app(app)
    cors.init_app(app)
    migrate.init_app(app, db)
    
    # 添加自定义过滤器
    @app.template_filter('number_format')
    def number_format_filter(value, field_name=None):
        """格式化数字，根据字段名决定精度"""
        try:
            if isinstance(value, (int, float, Decimal)):
                # 根据字段名确定格式化精度
                if field_name:
                    # 代币价格: 6位小数
                    if 'token_price' in field_name or 'price' in field_name:
                        return "{:,.6f}".format(float(value))
                    # 面积、总价值、年收益: 2位小数
                    elif any(field in field_name for field in ['area', 'total_value', 'annual_revenue']):
                        return "{:,.2f}".format(float(value))
                # 默认: 2位小数
                return "{:,.2f}".format(float(value))
            else:
                return value
        except (ValueError, TypeError):
            return value
    
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