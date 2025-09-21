"""
区块链集成模块
支持与以太坊和Solana区块链的交互
"""

# 导出主要的类
from .solana import SolanaClient
from .asset_service import AssetService

__all__ = ['SolanaClient', 'AssetService']
