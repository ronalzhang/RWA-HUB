from app import create_app, db
import os
from flask_migrate import upgrade

# 获取环境配置
env = os.environ.get('FLASK_ENV', 'development')
app = create_app(env)

def init_db():
    """初始化数据库"""
    try:
        # 运行数据库迁移
        with app.app_context():
            db.create_all()
            upgrade()
        print("数据库初始化成功！")
    except Exception as e:
        print(f"数据库初始化失败：{str(e)}")
        exit(1)

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
