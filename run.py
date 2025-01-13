import logging
from app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Starting application...")
    app = create_app()
    print("Starting server...")
    print("Access URLs:")
    print("Local:    http://127.0.0.1:3000")
    print("External: http://0.0.0.0:3000")
    app.run(host='0.0.0.0', port=3000, debug=True)