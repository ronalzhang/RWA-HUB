from app import create_app
import logging
import socket
import argparse

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
        return "127.0.0.1"

if __name__ == '__main__':
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='启动Flask应用服务器')
    parser.add_argument('--port', type=int, default=8080, help='服务器端口号')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='服务器主机地址')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    app = create_app()
    
    # 使用命令行参数中的端口和主机
    port = args.port
    host = args.host
    
    print("Starting server...")
    print("Access URLs:")
    print(f"Local:    http://127.0.0.1:{port}")
    print(f"Network:  http://{get_ip()}:{port}")
    
    app.run(host=host, port=port, debug=True)