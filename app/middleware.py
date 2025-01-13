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
        
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].replace('Bearer ', '')
            
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
            
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            user = User.query.get(data['user_id'])
            if not user:
                return jsonify({'error': 'Invalid token'}), 401
            g.current_user = user
        except:
            return jsonify({'error': 'Invalid token'}), 401
            
        return f(*args, **kwargs)
    return decorated

def eth_address_required(f):
    """验证用户是否绑定以太坊地址的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        eth_address = request.headers.get('X-Eth-Address')
        
        if not eth_address:
            return jsonify({'error': 'Wallet address is missing'}), 401
            
        # 验证地址格式
        if not eth_address.startswith('0x') or len(eth_address) != 42:
            return jsonify({'error': 'Invalid wallet address'}), 401
            
        g.eth_address = eth_address
        return f(*args, **kwargs)
    return decorated