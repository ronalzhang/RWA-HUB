from functools import wraps
from flask import request, jsonify, g
import jwt
from app.models.user import User
from flask import current_app

def token_required(f):
    """验证JWT令牌的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].replace("Bearer ", "")
            
        if not token:
            return jsonify({"error": "Token is missing"}), 401
            
        try:
            data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
            user = User.query.get(data["user_id"])
            if not user:
                return jsonify({"error": "Invalid token"}), 401
            g.current_user = user
        except:
            return jsonify({"error": "Invalid token"}), 401
            
        return f(*args, **kwargs)
    return decorated

def eth_address_required(f):
    """验证用户是否绑定以太坊地址的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 先检查X-Wallet-Address和X-Eth-Address头部
        eth_address = request.headers.get("X-Wallet-Address") or request.headers.get("X-Eth-Address")
        
        # 如果头部中没有，检查Cookie
        if not eth_address:
            eth_address = request.cookies.get("wallet_address") or request.cookies.get("eth_address")
            
        # 如果Cookie中没有，检查URL参数
        if not eth_address:
            eth_address = request.args.get("wallet_address") or request.args.get("eth_address")
           
        if not eth_address:
            current_app.logger.error("请求缺少钱包地址，所有可能的来源都检查过了")
            current_app.logger.debug(f"请求头: {dict(request.headers)}")
            return jsonify({"success": False, "error": "未提供钱包地址"}), 401
            
        # 在g对象中存储以太坊地址
        g.eth_address = eth_address
        g.wallet_address = eth_address  # 为兼容性添加
        current_app.logger.info(f"找到钱包地址: {eth_address}")
        
        return f(*args, **kwargs)
    return decorated

def wallet_address_required(f):
    """验证用户是否提供钱包地址的装饰器(适用于多种钱包类型)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 支持多种钱包地址头
        wallet_address = request.headers.get("X-Wallet-Address") or request.headers.get("X-Eth-Address")
        
        # 如果头部中没有，检查Cookie
        if not wallet_address:
            wallet_address = request.cookies.get("wallet_address") or request.cookies.get("eth_address")
            
        # 如果Cookie中没有，检查URL参数
        if not wallet_address:
            wallet_address = request.args.get("wallet_address") or request.args.get("eth_address")
           
        if not wallet_address:
            current_app.logger.error("请求缺少钱包地址，所有可能的来源都检查过了")
            current_app.logger.debug(f"请求头: {dict(request.headers)}")
            return jsonify({"success": False, "error": "未提供钱包地址"}), 401
           
        # 在g对象中存储钱包地址
        g.wallet_address = wallet_address
        g.eth_address = wallet_address  # 为兼容性添加
        current_app.logger.info(f"找到钱包地址: {wallet_address}")
        
        return f(*args, **kwargs)
    return decorated 