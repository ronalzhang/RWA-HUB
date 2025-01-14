from .main import main_bp
from .auth import auth_bp
from .assets import assets_bp
from .admin import admin_bp, admin_api_bp
from .api import auth_api_bp, assets_api_bp, trades_api_bp

__all__ = [
    'main_bp',
    'auth_bp',
    'assets_bp',
    'admin_bp',
    'auth_api_bp',
    'assets_api_bp',
    'trades_api_bp',
    'admin_api_bp'
]
