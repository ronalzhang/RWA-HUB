from app import create_app
import logging
import os

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 创建应用实例（使用环境变量或默认为development）
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == "__main__":
    logger.info("Starting application...")
    try:
        app.run(host="0.0.0.0", port=8000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise