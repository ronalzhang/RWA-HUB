from .. import db

# 先导入 Asset 模型，因为它被 DividendRecord 引用
from .asset import Asset, AssetType

# 然后导入 DividendRecord 模型
from .dividend import DividendRecord

# 导出所有模型
__all__ = ['db', 'Asset', 'AssetType', 'DividendRecord']
