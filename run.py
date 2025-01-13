from app import create_app
import logging
import socket

def get_ip():
    """获取本机IP地址"""
    try:
        # 通过连接一个外部服务器获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "0.0.0.0"

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    # 修改host为0.0.0.0允许外部访问
    print("Starting server...")
    print("Access URLs:")
    print("Local:    http://127.0.0.1:8080")
    print(f"Network:  http://{get_ip()}:8080")
    app.run(host='0.0.0.0', port=8080, debug=True)