"""
RWA-HUB 6.0 Performance Optimized Configuration
专为6.0版本设计的高性能配置文件
"""

import os
from datetime import timedelta
from typing import Dict, Any, Optional

class ConfigV6:
    """RWA-HUB 6.0 基础配置"""
    
    # 版本信息
    VERSION = '6.0.0'
    BUILD_DATE = '2025-07-08'
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'rwa-hub-v6-ultra-secure-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://rwa_hub_user:rwa_hub_pass@localhost/rwa_hub'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 性能优化配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 20,
        'max_overflow': 30,
        'pool_timeout': 30,
        'echo': False,
        'connect_args': {
            'sslmode': 'prefer',
            'connect_timeout': 10,
            'application_name': 'RWA-HUB-6.0'
        }
    }
    
    # Redis配置（性能优化）
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    REDIS_CONFIG = {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'decode_responses': True,
        'socket_connect_timeout': 5,
        'socket_timeout': 5,
        'retry_on_timeout': True,
        'health_check_interval': 30,
        'max_connections': 100
    }
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    
    # 缓存配置
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_KEY_PREFIX = 'rwa_hub_v6:'
    CACHE_REDIS_HOST = 'localhost'
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 1
    
    # 会话配置
    SESSION_TYPE = 'redis'
    SESSION_REDIS_HOST = 'localhost'
    SESSION_REDIS_PORT = 6379
    SESSION_REDIS_DB = 2
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'rwa_hub_session:'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'csv'}
    
    # 邮件配置
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@rwa-hub.com'
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = 'logs/rwa-hub-v6.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # 安全配置
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or 'rwa-hub-v6-salt'
    SECURITY_REGISTERABLE = True
    SECURITY_CONFIRMABLE = True
    SECURITY_RECOVERABLE = True
    SECURITY_TRACKABLE = True
    SECURITY_CHANGEABLE = True
    SECURITY_SEND_REGISTER_EMAIL = True
    
    # API限流配置
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "1000 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    
    # 国际化配置
    LANGUAGES = {
        'en': 'English',
        'zh': '中文',
        'ja': '日本語',
        'ko': '한국어'
    }
    BABEL_DEFAULT_LOCALE = 'zh'
    BABEL_DEFAULT_TIMEZONE = 'UTC'
    
    # 前端配置
    FRONTEND_CONFIG = {
        'theme': 'dark-glass',
        'version': VERSION,
        'features': {
            'real_time_updates': True,
            'dark_mode': True,
            'animations': True,
            'notifications': True,
            'progressive_web_app': True
        },
        'performance': {
            'lazy_loading': True,
            'image_optimization': True,
            'code_splitting': True,
            'service_worker': True
        }
    }
    
    # WebSocket配置
    SOCKETIO_ASYNC_MODE = 'threading'
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
    SOCKETIO_PING_TIMEOUT = 60
    SOCKETIO_PING_INTERVAL = 25
    
    # 区块链配置
    BLOCKCHAIN_CONFIG = {
        'ethereum': {
            'rpc_url': os.environ.get('ETHEREUM_RPC_URL') or 'https://mainnet.infura.io/v3/YOUR_PROJECT_ID',
            'chain_id': 1,
            'gas_limit': 500000,
            'gas_price': 'auto'
        },
        'solana': {
            'rpc_url': os.environ.get('SOLANA_RPC_URL') or 'https://api.mainnet-beta.solana.com',
            'commitment': 'confirmed'
        },
        'polygon': {
            'rpc_url': os.environ.get('POLYGON_RPC_URL') or 'https://polygon-rpc.com',
            'chain_id': 137,
            'gas_limit': 300000
        }
    }
    
    # 监控配置
    MONITORING = {
        'enabled': True,
        'metrics_port': 9090,
        'health_check_interval': 30,
        'alert_thresholds': {
            'cpu_usage': 80,
            'memory_usage': 85,
            'disk_usage': 90,
            'response_time': 2000  # ms
        }
    }

class DevelopmentConfigV6(ConfigV6):
    """开发环境配置"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'
    
    # 开发环境特定配置
    FRONTEND_CONFIG = {
        **ConfigV6.FRONTEND_CONFIG,
        'features': {
            **ConfigV6.FRONTEND_CONFIG['features'],
            'debug_mode': True,
            'hot_reload': True
        }
    }

class ProductionConfigV6(ConfigV6):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    # 生产环境安全配置
    SECURITY_PASSWORD_COMPLEXITY_CHECKER = 'zxcvbn'
    SECURITY_PASSWORD_LENGTH_MIN = 12
    SECURITY_PASSWORD_REQUIRE_UPPERCASE = True
    SECURITY_PASSWORD_REQUIRE_LOWERCASE = True
    SECURITY_PASSWORD_REQUIRE_NUMBERS = True
    SECURITY_PASSWORD_REQUIRE_SPECIAL = True
    
    # 生产环境性能配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        **ConfigV6.SQLALCHEMY_ENGINE_OPTIONS,
        'pool_size': 50,
        'max_overflow': 100,
        'pool_recycle': 1800
    }
    
    # 生产环境监控
    MONITORING = {
        **ConfigV6.MONITORING,
        'alert_thresholds': {
            'cpu_usage': 70,
            'memory_usage': 75,
            'disk_usage': 80,
            'response_time': 1000
        }
    }

class TestingConfigV6(ConfigV6):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # 测试环境特定配置
    CACHE_TYPE = 'simple'
    RATELIMIT_ENABLED = False

# 配置字典
config_v6 = {
    'development': DevelopmentConfigV6,
    'production': ProductionConfigV6,
    'testing': TestingConfigV6,
    'default': DevelopmentConfigV6
}

def get_config(config_name: Optional[str] = None) -> ConfigV6:
    """获取配置对象"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG') or 'default'
    
    return config_v6.get(config_name, config_v6['default'])

def get_frontend_config() -> Dict[str, Any]:
    """获取前端配置"""
    config = get_config()
    return config.FRONTEND_CONFIG

def get_performance_config() -> Dict[str, Any]:
    """获取性能配置"""
    config = get_config()
    return {
        'database': config.SQLALCHEMY_ENGINE_OPTIONS,
        'redis': config.REDIS_CONFIG,
        'cache': {
            'type': config.CACHE_TYPE,
            'timeout': config.CACHE_DEFAULT_TIMEOUT
        },
        'session': {
            'lifetime': config.PERMANENT_SESSION_LIFETIME.total_seconds()
        },
        'monitoring': config.MONITORING
    } 