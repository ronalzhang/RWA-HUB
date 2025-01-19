from app import create_app, db
import os
from flask_migrate import upgrade

# 获取环境配置
env = os.environ.get('FLASK_ENV', 'development')
app = create_app(env)

def init_db():
    try:
        # 尝试删除现有的数据库文件
        if os.path.exists('instance/app.db'):
            os.remove('instance/app.db')
            logger.info("Removed existing database file")
    except Exception as e:
        logger.warning(f"Error removing database file: {e}")

    try:
        # 确保 instance 目录存在
        os.makedirs('instance', exist_ok=True)
        
        # 创建所有表
        with create_app().app_context():
            db.create_all()
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == '__main__':
    # 确保上传目录存在
    upload_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    os.makedirs(upload_folder, exist_ok=True)
    
    # 初始化数据库
    init_db()
    
    # 启动服务器
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 8000))
    
    print(f"\n{'='*50}")
    print(f"服务器启动于: http://{host}:{port}")
    print(f"运行环境: {env}")
    print(f"调试模式: {'开启' if app.debug else '关闭'}")
    print(f"{'='*50}\n")
    
    if env == 'production':
        from waitress import serve
        serve(app, host=host, port=port)
    else:
        app.run(host=host, port=port)
