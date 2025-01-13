import os

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def write_file(path, content):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated: {path}")

# 所有文件的内容
FILES = {
    # 用户模型
    'app/models/user.py': '''from datetime import datetime, UTC
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    eth_address = db.Column(db.String(42), unique=True)
    nonce = db.Column(db.String(100))  # 用于以太坊签名验证
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def __init__(self, username: str, email: str, eth_address: str = None):
        self.username = username
        self.email = email
        self.eth_address = eth_address

    def set_password(self, password: str):
        """设置密码"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "eth_address": self.eth_address,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
''',

    # 资产模型
    'app/models/asset.py': '''from enum import IntEnum
from datetime import datetime, UTC
from typing import List, Optional
from app import db
import json

class AssetType(IntEnum):
    """资产类型枚举"""
    REAL_ESTATE = 10  # 不动产
    NON_REAL_ESTATE = 20  # 类不动产

class Asset(db.Model):
    """资产模型"""
    __tablename__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    asset_type = db.Column(db.Integer, nullable=False)
    area = db.Column(db.Float)
    total_value = db.Column(db.Float)
    token_price = db.Column(db.Float, nullable=False)
    token_supply = db.Column(db.Integer)
    location = db.Column(db.String(200), nullable=False)
    owner_address = db.Column(db.String(42), nullable=False)
    token_symbol = db.Column(db.String(10))
    _images = db.Column('images', db.Text)
    _documents = db.Column('documents', db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    @property
    def images(self) -> List[str]:
        return json.loads(self._images) if self._images else []

    @images.setter
    def images(self, value: List[str]):
        self._images = json.dumps(value) if value else None

    @property
    def documents(self) -> List[str]:
        return json.loads(self._documents) if self._documents else []

    @documents.setter
    def documents(self, value: List[str]):
        self._documents = json.dumps(value) if value else None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "asset_type": self.asset_type,
            "area": self.area,
            "total_value": self.total_value,
            "token_price": self.token_price,
            "token_supply": self.token_supply,
            "location": self.location,
            "owner_address": self.owner_address,
            "token_symbol": self.token_symbol,
            "images": self.images,
            "documents": self.documents,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
''',

    # 认证路由
    'app/routes/auth.py': '''from datetime import datetime, UTC
from flask import jsonify, request, current_app
from eth_account.messages import encode_defunct
from web3 import Web3
from . import auth_bp
from app.models.user import User
from app import db
import random
import string
import jwt

def generate_nonce() -> str:
    """生成随机nonce"""
    timestamp = datetime.now(UTC).timestamp()
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"Welcome to 58HUB! Please sign this message to verify your identity. Nonce: {timestamp}-{random_str}"

@auth_bp.route("/register", methods=["POST"])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        eth_address = data.get("eth_address")

        # 验证必填字段
        if not all([username, email, password]):
            return jsonify({"error": "Missing required fields"}), 400

        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists"}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 400
        if eth_address and User.query.filter_by(eth_address=eth_address).first():
            return jsonify({"error": "ETH address already exists"}), 400

        # 创建新用户
        user = User(username=username, email=email, eth_address=eth_address)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()

        return jsonify(user.to_dict()), 201

    except Exception as e:
        current_app.logger.error(f"Registration failed: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400

        # 查找用户
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid username or password"}), 401

        # 生成JWT令牌
        token = jwt.encode(
            {
                "user_id": user.id,
                "username": user.username,
                "exp": datetime.now(UTC).timestamp() + 86400  # 24小时过期
            },
            current_app.config["SECRET_KEY"],
            algorithm="HS256"
        )

        return jsonify({
            "token": token,
            "user": user.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Login failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/nonce", methods=["POST"])
def get_nonce():
    """获取用于以太坊签名的nonce"""
    try:
        data = request.get_json()
        eth_address = data.get("address")

        if not eth_address:
            return jsonify({"error": "ETH address is required"}), 400

        # 查找或创建用户
        user = User.query.filter_by(eth_address=eth_address).first()
        if not user:
            user = User(
                username=f"user_{eth_address[:8]}",
                email=f"{eth_address[:8]}@58hub.eth",
                eth_address=eth_address
            )
            db.session.add(user)

        # 生成新的nonce
        user.nonce = generate_nonce()
        db.session.commit()

        return jsonify({
            "nonce": user.nonce,
            "address": eth_address
        })

    except Exception as e:
        current_app.logger.error(f"Get nonce failed: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/verify-signature", methods=["POST"])
def verify_signature():
    """验证以太坊签名"""
    try:
        data = request.get_json()
        eth_address = data.get("address")
        signature = data.get("signature")

        if not eth_address or not signature:
            return jsonify({"error": "Address and signature are required"}), 400

        # 查找用户
        user = User.query.filter_by(eth_address=eth_address).first()
        if not user or not user.nonce:
            return jsonify({"error": "Invalid address or nonce"}), 401

        # 验证签名
        w3 = Web3()
        message = encode_defunct(text=user.nonce)
        recovered_address = w3.eth.account.recover_message(message, signature=signature)

        if recovered_address.lower() != eth_address.lower():
            return jsonify({"error": "Invalid signature"}), 401

        # 生成新的nonce
        user.nonce = generate_nonce()
        db.session.commit()

        # 生成JWT令牌
        token = jwt.encode(
            {
                "user_id": user.id,
                "username": user.username,
                "eth_address": user.eth_address,
                "exp": datetime.now(UTC).timestamp() + 86400  # 24小时过期
            },
            current_app.config["SECRET_KEY"],
            algorithm="HS256"
        )

        return jsonify({
            "token": token,
            "user": user.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Verify signature failed: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
''',

    # 认证中间件
    'app/middleware.py': '''from functools import wraps
from flask import request, jsonify, current_app, g
import jwt
from app.models.user import User

def token_required(f):
    """验证JWT令牌的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # 从请求头获取令牌
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Invalid token format"}), 401
        
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        try:
            # 验证令牌
            data = jwt.decode(
                token,
                current_app.config["SECRET_KEY"],
                algorithms=["HS256"]
            )
            
            # 获取用户信息
            current_user = User.query.get(data["user_id"])
            if not current_user:
                return jsonify({"error": "User not found"}), 401
            
            # 存储用户信息到g对象
            g.current_user = current_user
            
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def eth_address_required(f):
    """验证用户是否绑定以太坊地址的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.current_user.eth_address:
            return jsonify({"error": "ETH address is required"}), 403
        return f(*args, **kwargs)
    
    return decorated
''',

    # 前端模板 - 登录页面
    'app/templates/auth/login.html': '''{% extends "base.html" %}

{% block title %}登录 - 58HUB{% endblock %}

{% block content %}
<div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
        <div>
            <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
                登录您的账户
            </h2>
        </div>
        <div class="mt-8 space-y-6">
            <div class="rounded-md shadow-sm -space-y-px">
                <div>
                    <label for="username" class="sr-only">用户名</label>
                    <input id="username" name="username" type="text" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                           placeholder="用户名">
                </div>
                <div>
                    <label for="password" class="sr-only">密码</label>
                    <input id="password" name="password" type="password" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                           placeholder="密码">
                </div>
            </div>

            <div>
                <button type="button" onclick="login()"
                        class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    登录
                </button>
            </div>

            <div class="text-center">
                <p class="text-sm text-gray-600">
                    或者
                </p>
                <button type="button" onclick="connectWallet()"
                        class="mt-3 w-full inline-flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    使用MetaMask登录
                </button>
            </div>
        </div>
    </div>
</div>

<script>
async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            // 保存令牌
            localStorage.setItem('token', data.token);
            // 跳转到首页
            window.location.href = '/';
        } else {
            alert(data.error || '登录失败');
        }
    } catch (error) {
        console.error('登录失败:', error);
        alert('登录失败，请重试');
    }
}

async function connectWallet() {
    if (typeof window.ethereum === 'undefined') {
        alert('请安装MetaMask钱包');
        return;
    }

    try {
        // 请求连接钱包
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        const address = accounts[0];

        // 获取nonce
        const nonceResponse = await fetch('/api/auth/nonce', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ address })
        });
        const nonceData = await nonceResponse.json();

        // 请求签名
        const signature = await window.ethereum.request({
            method: 'personal_sign',
            params: [nonceData.nonce, address]
        });

        // 验证签名
        const verifyResponse = await fetch('/api/auth/verify-signature', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                address,
                signature
            })
        });

        const verifyData = await verifyResponse.json();

        if (verifyResponse.ok) {
            // 保存令牌
            localStorage.setItem('token', verifyData.token);
            // 跳转到首页
            window.location.href = '/';
        } else {
            alert(verifyData.error || '登录失败');
        }
    } catch (error) {
        console.error('MetaMask登录失败:', error);
        alert('登录失败，请重试');
    }
}
</script>
{% endblock %}
''',

    # 基础模板
    'app/templates/base.html': '''<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}58HUB - 资产管理平台{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between h-16">
                <div class="flex">
                    <div class="flex-shrink-0 flex items-center">
                        <a href="/" class="text-xl font-bold text-gray-800">58HUB</a>
                    </div>
                    <div class="hidden md:ml-6 md:flex md:space-x-8">
                        <a href="/assets" class="inline-flex items-center px-1 pt-1 text-gray-600 hover:text-gray-900">资产列表</a>
                        <a href="/assets/create" class="inline-flex items-center px-1 pt-1 text-gray-600 hover:text-gray-900">创建资产</a>
                    </div>
                </div>
                <div class="flex items-center">
                    <div id="userInfo" class="hidden">
                        <span class="text-gray-700 mr-4" id="username"></span>
                        <button onclick="logout()" class="text-gray-600 hover:text-gray-900">退出</button>
                    </div>
                    <div id="loginButton" class="hidden">
                        <a href="/auth/login" class="text-gray-600 hover:text-gray-900">登录</a>
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {% block content %}{% endblock %}
    </main>

    <script>
    // 检查登录状态
    function checkAuth() {
        const token = localStorage.getItem('token');
        const userInfo = document.getElementById('userInfo');
        const loginButton = document.getElementById('loginButton');
        
        if (token) {
            userInfo.classList.remove('hidden');
            loginButton.classList.add('hidden');
            // 解析JWT获取用户名
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                document.getElementById('username').textContent = payload.username;
            } catch (e) {
                console.error('Invalid token:', e);
            }
        } else {
            userInfo.classList.add('hidden');
            loginButton.classList.remove('hidden');
        }
    }

    function logout() {
        localStorage.removeItem('token');
        window.location.href = '/auth/login';
    }

    document.addEventListener('DOMContentLoaded', checkAuth);
    </script>
</body>
</html>
'''
}

def main():
    """主函数"""
    # 获取脚本所在目录的父目录（项目根目录）
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 更新所有文件
    for path, content in FILES.items():
        full_path = os.path.join(root_dir, path)
        write_file(full_path, content)

if __name__ == "__main__":
    main()