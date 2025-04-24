from flask import Flask
from waitress import serve

# 创建测试应用
app = Flask(__name__)

@app.route('/')
def test():
    return "Direct WSGI test successful"

if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=9000) 