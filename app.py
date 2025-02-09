from app import create_app
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = create_app()

if __name__ == "__main__":
    logger.info("Starting application...")
    try:
        app.run(host="0.0.0.0", port=10000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise