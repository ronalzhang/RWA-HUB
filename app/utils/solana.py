from base64 import b64encode, b64decode
import json
import os
import time
# from solana.rpc.api import Client
# from solana.rpc.types import TxOpts
# from solana.transaction import Transaction, AccountMeta
# from solana.publickey import PublicKey
# from solana.keypair import Keypair
# from solana.system_program import SYS_PROGRAM_ID, create_account
# 使用我们的兼容层
from app.utils.solana_compat.rpc.api import Client
from app.utils.solana_compat.rpc.types import TxOpts
from app.utils.solana_compat.transaction import Transaction, AccountMeta, TransactionInstruction
from app.utils.solana_compat.publickey import PublicKey
from app.utils.solana_compat.keypair import Keypair
from app.utils.solana_compat.system_program import SystemProgram as SYS_PROGRAM

import logging
from typing import List, Optional, Dict, Any, Tuple
import requests

SYS_PROGRAM_ID = SYS_PROGRAM.PROGRAM_ID

# from solana.transaction import TransactionInstruction
# 函数导入
import struct
from app.utils.helpers import check_response

# 修复导入问题
try:
    from spl.token.instructions import get_associated_token_address, create_associated_token_account_instruction
except ImportError:
    # 如果无法导入，提供替代实现
    def get_associated_token_address(owner, mint):
        """获取关联代币账户地址"""
        return PublicKey(str(owner)[:32])  # 模拟实现，仅用于测试
    
    def create_associated_token_account_instruction():
        """创建关联代币账户指令"""
        pass  # 模拟实现，仅用于测试
        
from spl.token.constants import TOKEN_PROGRAM_ID

# 配置信息
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")
# 使用一个有效的测试程序 ID
PROGRAM_ID = os.environ.get("SOLANA_PROGRAM_ID", "HmbTLCmaGvZhKnn1Zfa1JVnp7vkMV4DYVxPLWBVoN65")
USDC_MINT = os.environ.get("SOLANA_USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")

# 指令类型枚举
INSTRUCTION_INITIALIZE_ASSET = 0
INSTRUCTION_BUY = 1
INSTRUCTION_DIVIDEND = 2

class SolanaClient:
    """Solana 客户端工具类"""
    
    def __init__(self):
        self.client = Client(SOLANA_RPC_URL)
        self.program_id = PublicKey(PROGRAM_ID)
        self.usdc_mint = PublicKey(USDC_MINT)
    
    def get_account_info(self, pubkey):
        """获取账户信息"""
        response = self.client.get_account_info(pubkey)
        return response["result"]["value"]
    
    def get_asset_account(self, asset_id):
        """获取资产账户"""
        # 使用资产ID作为种子派生PDA
        asset_seed = f"asset-{asset_id}".encode()
        asset_pubkey, _ = PublicKey.find_program_address(
            [asset_seed], self.program_id
        )
        return asset_pubkey
    
    def get_dividend_pool(self, asset_id):
        """获取分红池账户"""
        # 使用资产ID作为种子派生PDA
        dividend_seed = f"dividend-{asset_id}".encode()
        dividend_pubkey, _ = PublicKey.find_program_address(
            [dividend_seed], self.program_id
        )
        return dividend_pubkey
    
    def get_asset_mint(self, asset_id):
        """获取资产代币铸造账户"""
        # 使用资产ID作为种子派生PDA
        mint_seed = f"mint-{asset_id}".encode()
        mint_pubkey, _ = PublicKey.find_program_address(
            [mint_seed], self.program_id
        )
        return mint_pubkey
    
    def get_token_account(self, owner, mint):
        """获取代币账户地址"""
        return get_associated_token_address(owner, mint)
    
    def create_asset(self, owner_keypair, asset_id, name, symbol, total_supply, decimals=0):
        """创建资产"""
        owner = PublicKey(owner_keypair.public_key)
        asset_pubkey = self.get_asset_account(asset_id)
        mint_pubkey = self.get_asset_mint(asset_id)
        
        # 创建交易指令
        transaction = Transaction()
        
        # 添加创建资产指令
        # 封装指令数据
        instruction_data = struct.pack(
            "<B" +   # 指令类型 (1 byte)
            "I" +    # 资产ID (4 bytes)
            f"{len(name)}s" +   # 名称
            f"{len(symbol)}s" +   # 符号
            "Q" +    # 总供应量 (8 bytes)
            "B",     # 小数位数 (1 byte)
            INSTRUCTION_INITIALIZE_ASSET,
            asset_id,
            name.encode(),
            symbol.encode(),
            total_supply,
            decimals
        )
        
        # 创建指令
        initialize_asset_instruction = TransactionInstruction(
            keys=[
                AccountMeta(owner, True, True),               # 创建者
                AccountMeta(asset_pubkey, False, True),       # 资产账户
                AccountMeta(mint_pubkey, False, True),        # 代币铸造账户
                AccountMeta(SYS_PROGRAM_ID, False, False),    # 系统程序
                AccountMeta(TOKEN_PROGRAM_ID, False, False),  # 代币程序
            ],
            program_id=self.program_id,
            data=instruction_data
        )
        
        # 添加到交易
        transaction.add(initialize_asset_instruction)
        
        # 签名并发送交易
        txid = self.client.send_transaction(
            transaction, owner_keypair, opts=TxOpts(skip_preflight=False)
        )
        return {"transaction_id": txid["result"], "asset_account": str(asset_pubkey), "mint_account": str(mint_pubkey)}
    
    def buy_asset(self, buyer_keypair, asset_id, amount):
        """购买资产代币"""
        buyer = PublicKey(buyer_keypair.public_key)
        asset_pubkey = self.get_asset_account(asset_id)
        mint_pubkey = self.get_asset_mint(asset_id)
        
        # 获取代币账户
        buyer_token_account = self.get_token_account(buyer, mint_pubkey)
        buyer_usdc_account = self.get_token_account(buyer, self.usdc_mint)
        
        # 获取资产信息以获取所有者信息
        asset_info = self.get_account_info(asset_pubkey)
        if not asset_info:
            raise ValueError(f"资产 {asset_id} 不存在")
        
        # 这里需要解析资产数据以获取所有者地址
        # 为简化，假设我们有解析函数
        seller = PublicKey("11111111111111111111111111111111")  # 替换为实际所有者地址
        seller_token_account = self.get_token_account(seller, mint_pubkey)
        seller_usdc_account = self.get_token_account(seller, self.usdc_mint)
        
        # 创建交易指令
        transaction = Transaction()
        
        # 封装购买指令数据
        instruction_data = struct.pack(
            "<BQ",   # 指令类型 (1 byte) + 数量 (8 bytes)
            INSTRUCTION_BUY,
            amount
        )
        
        # 创建购买指令
        buy_instruction = TransactionInstruction(
            keys=[
                AccountMeta(buyer, True, True),                 # 买家
                AccountMeta(buyer_token_account, False, True),  # 买家代币账户
                AccountMeta(seller_token_account, False, True), # 卖家代币账户
                AccountMeta(buyer_usdc_account, False, True),   # 买家USDC账户
                AccountMeta(seller_usdc_account, False, True),  # 卖家USDC账户
                AccountMeta(TOKEN_PROGRAM_ID, False, False),    # 代币程序
                AccountMeta(asset_pubkey, False, True),         # 资产账户
            ],
            program_id=self.program_id,
            data=instruction_data
        )
        
        # 添加到交易
        transaction.add(buy_instruction)
        
        # 签名并发送交易
        txid = self.client.send_transaction(
            transaction, buyer_keypair, opts=TxOpts(skip_preflight=False)
        )
        return {"transaction_id": txid["result"]}
    
    def create_dividend(self, owner_keypair, asset_id, amount):
        """创建分红"""
        owner = PublicKey(owner_keypair.public_key)
        asset_pubkey = self.get_asset_account(asset_id)
        dividend_pool = self.get_dividend_pool(asset_id)
        owner_usdc_account = self.get_token_account(owner, self.usdc_mint)
        
        # 创建交易指令
        transaction = Transaction()
        
        # 封装分红指令数据
        instruction_data = struct.pack(
            "<BQ",   # 指令类型 (1 byte) + 金额 (8 bytes)
            INSTRUCTION_DIVIDEND,
            amount
        )
        
        # 创建分红指令
        dividend_instruction = TransactionInstruction(
            keys=[
                AccountMeta(owner, True, True),               # 所有者
                AccountMeta(dividend_pool, False, True),      # 分红池账户
                AccountMeta(owner_usdc_account, False, True), # 所有者USDC账户
                AccountMeta(TOKEN_PROGRAM_ID, False, False),  # 代币程序
                AccountMeta(asset_pubkey, False, True),       # 资产账户
            ],
            program_id=self.program_id,
            data=instruction_data
        )
        
        # 添加到交易
        transaction.add(dividend_instruction)
        
        # 签名并发送交易
        txid = self.client.send_transaction(
            transaction, owner_keypair, opts=TxOpts(skip_preflight=False)
        )
        return {"transaction_id": txid["result"], "dividend_pool": str(dividend_pool)}
    
    @staticmethod
    def load_keypair(keypair_path):
        """从文件加载密钥对"""
        with open(keypair_path, 'r') as f:
            keypair_bytes = json.loads(f.read())
            return Keypair.from_secret_key(bytes(keypair_bytes))
            
    @staticmethod
    def create_keypair():
        """创建新的密钥对"""
        return Keypair.generate()

# 单例实例
solana_client = SolanaClient() 