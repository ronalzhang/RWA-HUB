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
from app.utils.solana_compat.token.instructions import get_associated_token_address, create_associated_token_account_instruction
from app.utils.solana_compat.token.constants import TOKEN_PROGRAM_ID

import logging
from typing import List, Optional, Dict, Any, Tuple
import requests

SYS_PROGRAM_ID = SYS_PROGRAM.PROGRAM_ID

# from solana.transaction import TransactionInstruction
# 函数导入
import struct
from app.utils.helpers import check_response

# 配置信息
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")
# 使用一个有效的测试程序 ID
USDC_MINT = os.environ.get("SOLANA_USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
PROGRAM_ID = os.environ.get("SOLANA_PROGRAM_ID", "9AcvoQmz22KRcMhkLkeSkKs8W7ru6oae8GHcxrS83fKz")
PLATFORM_FEE_ADDRESS = os.environ.get("PLATFORM_FEE_ADDRESS", "HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd")

# 指令类型枚举
INSTRUCTION_INITIALIZE_ASSET = 0
INSTRUCTION_BUY = 1
INSTRUCTION_DIVIDEND = 2

class SolanaClient:
    """Solana 客户端工具类"""
    
    def __init__(self):
        # 尝试使用多个RPC节点以增加可靠性
        self.rpc_nodes = [
            SOLANA_RPC_URL,
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
            "https://rpc.ankr.com/solana"
        ]
        
        self.client = None
        self._init_client()
        
        self.program_id = PublicKey(PROGRAM_ID)
        self.usdc_mint = PublicKey(USDC_MINT)
        self.platform_fee_address = PublicKey(PLATFORM_FEE_ADDRESS)
    
    def _init_client(self):
        """初始化Solana RPC客户端，尝试多个节点"""
        for rpc_url in self.rpc_nodes:
            try:
                logging.info(f"尝试连接Solana RPC节点: {rpc_url}")
                test_client = Client(rpc_url)
                
                # 测试连接是否可用
                response = test_client.get_health()
                if response and 'result' in response and response['result'] == 'ok':
                    logging.info(f"成功连接到Solana RPC节点: {rpc_url}")
                    self.client = test_client
                    return
                else:
                    logging.warning(f"Solana RPC节点连接测试失败: {rpc_url}, 响应: {response}")
            except Exception as e:
                logging.warning(f"连接Solana RPC节点失败: {rpc_url}, 错误: {str(e)}")
        
        # 如果所有节点都失败，使用默认节点
        logging.warning("所有RPC节点连接失败，使用默认设置")
        self.client = Client(SOLANA_RPC_URL)
        
    def get_account_info(self, pubkey):
        """获取账户信息"""
        try:
            response = self.client.get_account_info(pubkey)
            if 'error' in response:
                logging.error(f"获取账户信息失败: {response['error']}")
                # 尝试重新初始化客户端
                self._init_client()
                # 重试一次
                response = self.client.get_account_info(pubkey)
                
            return response["result"]["value"]
        except Exception as e:
            logging.error(f"获取账户信息异常: {str(e)}")
            # 尝试重新初始化客户端后再次尝试
            try:
                self._init_client()
                response = self.client.get_account_info(pubkey)
                return response["result"]["value"]
            except Exception as retry_e:
                logging.error(f"重试获取账户信息也失败: {str(retry_e)}")
                raise
    
    def get_asset_account(self, asset_id):
        """获取资产账户"""
        # 使用资产ID作为种子派生PDA
        asset_seed = f"asset-{asset_id}".encode()
        asset_pubkey, _ = PublicKey.find_program_address(
            [asset_seed], self.program_id
        )
        return asset_pubkey
    
    def get_dividend_pool(self):
        """获取分红池PDA地址"""
        pool_seed = b"pool"
        pool_pubkey, _ = PublicKey.find_program_address(
            [pool_seed], self.program_id
        )
        return pool_pubkey
    
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
    
    def get_token_account_balance(self, token_account):
        """获取代币账户余额"""
        try:
            response = self.client.get_token_account_balance(token_account)
            return float(response["result"]["value"]["amount"]) / (10 ** response["result"]["value"]["decimals"])
        except Exception as e:
            logging.error(f"获取代币余额失败: {str(e)}")
            return 0
    
    def get_platform_token_account(self):
        """获取平台USDC代币账户"""
        return get_associated_token_address(self.platform_fee_address, self.usdc_mint)
    
    def create_asset(self, owner_keypair, name: str, symbol: str, total_supply: int, price: float, decimals: int = 0) -> Dict[str, str]:
        """创建资产"""
        try:
            # 转换价格为lamports (USDC有6位小数)
            price_lamports = int(price * 1e6)
            
            # 获取相关账户
            owner = PublicKey(owner_keypair.public_key)
            asset_pubkey = self.get_asset_account(symbol)
            mint_pubkey = self.get_asset_mint(symbol)
            
            # 创建交易
            transaction = Transaction()
            
            # 创建资产指令
            create_asset_instruction = TransactionInstruction(
                keys=[
                    AccountMeta(asset_pubkey, False, True),           # 资产账户
                    AccountMeta(owner, True, True),                   # 所有者
                    AccountMeta(mint_pubkey, False, True),           # 代币铸造账户
                    AccountMeta(SYS_PROGRAM_ID, False, False),       # 系统程序
                    AccountMeta(TOKEN_PROGRAM_ID, False, False),     # 代币程序
                    AccountMeta(RentSysvarPubkey, False, False),     # 租金系统变量
                ],
                program_id=self.program_id,
                data=struct.pack(
                    "<B32s32sQQB",
                    0,  # 0表示create_asset指令
                    name.encode('utf-8').ljust(32, b'\0'),
                    symbol.encode('utf-8').ljust(32, b'\0'),
                    total_supply,
                    price_lamports,
                    decimals
                )
            )
            
            transaction.add(create_asset_instruction)
            
            # 发送交易
            result = self.client.send_transaction(
                transaction,
                [owner_keypair],
                opts=TxOpts(skip_preflight=False)
            )
            
            return {
                "transaction_id": result["result"],
                "asset_pubkey": str(asset_pubkey),
                "mint_pubkey": str(mint_pubkey)
            }
            
        except Exception as e:
            logging.error(f"创建资产失败: {str(e)}")
            raise

    def buy_asset(self, buyer_keypair, symbol: str, amount: int) -> str:
        """购买资产"""
        try:
            # 获取相关账户
            buyer = PublicKey(buyer_keypair.public_key)
            asset_pubkey = self.get_asset_account(symbol)
            mint_pubkey = self.get_asset_mint(symbol)
            buyer_token_account = self.get_token_account(buyer, mint_pubkey)
            buyer_usdc_account = self.get_token_account(buyer, self.usdc_mint)
            platform_usdc_account = self.get_platform_token_account()
            
            # 创建交易
            transaction = Transaction()
            
            # 创建购买指令
            buy_instruction = TransactionInstruction(
                keys=[
                    AccountMeta(asset_pubkey, False, True),           # 资产账户
                    AccountMeta(buyer, True, True),                   # 买家
                    AccountMeta(mint_pubkey, False, True),           # 代币铸造账户
                    AccountMeta(buyer_token_account, False, True),    # 买家代币账户
                    AccountMeta(buyer_usdc_account, False, True),     # 买家USDC账户
                    AccountMeta(platform_usdc_account, False, True),  # 平台USDC账户
                    AccountMeta(TOKEN_PROGRAM_ID, False, False),      # 代币程序
                ],
                program_id=self.program_id,
                data=struct.pack("<BQ", 3, amount)  # 3表示buy_asset指令
            )
            
            transaction.add(buy_instruction)
            
            # 发送交易
            result = self.client.send_transaction(
                transaction,
                [buyer_keypair],
                opts=TxOpts(skip_preflight=False)
            )
            
            return result["result"]
            
        except Exception as e:
            logging.error(f"购买资产失败: {str(e)}")
            raise
    
    def create_dividend(self, owner_keypair, asset_id, amount):
        """创建分红"""
        owner = PublicKey(owner_keypair.public_key)
        asset_pubkey = self.get_asset_account(asset_id)
        dividend_pool = self.get_dividend_pool()
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
    
    def transfer_dividend_to_platform(self, amount: float, distributor: str, platform_address: str) -> str:
        """将分红金额转入平台PDA账户"""
        try:
            # 转换金额为lamports (USDC有6位小数)
            amount_lamports = int(amount * 1e6)
            
            # 获取相关账户
            distributor_pubkey = PublicKey(distributor)
            distributor_token_account = get_associated_token_address(distributor_pubkey, self.usdc_mint)
            platform_pubkey = PublicKey(platform_address)
            platform_token_account = get_associated_token_address(platform_pubkey, self.usdc_mint)
            pool_pubkey = self.get_dividend_pool()
            
            # 创建交易
            transaction = Transaction()
            
            # 创建转账指令
            transfer_instruction = TransactionInstruction(
                keys=[
                    AccountMeta(pool_pubkey, False, True),           # 分红池PDA
                    AccountMeta(distributor_pubkey, True, True),     # 发起人
                    AccountMeta(distributor_token_account, False, True),  # 发起人USDC账户
                    AccountMeta(platform_token_account, False, True), # 平台USDC账户
                    AccountMeta(TOKEN_PROGRAM_ID, False, False),     # 代币程序
                ],
                program_id=self.program_id,
                data=struct.pack("<BQ", 1, amount_lamports)  # 1表示transfer_dividend_to_platform指令
            )
            
            transaction.add(transfer_instruction)
            
            # 发送交易
            result = self.client.send_transaction(
                transaction,
                opts=TxOpts(skip_preflight=False)
            )
            
            return result["result"]
            
        except Exception as e:
            logging.error(f"转账分红到平台失败: {str(e)}")
            raise
    
    def process_withdrawal(self, amount: float, user: str, platform_address: str) -> str:
        """处理提现请求"""
        try:
            # 转换金额为lamports
            amount_lamports = int(amount * 1e6)
            
            # 获取相关账户
            user_pubkey = PublicKey(user)
            user_token_account = get_associated_token_address(user_pubkey, self.usdc_mint)
            platform_pubkey = PublicKey(platform_address)
            platform_token_account = get_associated_token_address(platform_pubkey, self.usdc_mint)
            pool_pubkey = self.get_dividend_pool()
            
            # 创建交易
            transaction = Transaction()
            
            # 创建提现指令
            withdrawal_instruction = TransactionInstruction(
                keys=[
                    AccountMeta(pool_pubkey, False, True),           # 分红池PDA
                    AccountMeta(user_pubkey, True, True),           # 用户
                    AccountMeta(platform_token_account, False, True), # 平台USDC账户
                    AccountMeta(user_token_account, False, True),    # 用户USDC账户
                    AccountMeta(self.usdc_mint, False, False),       # USDC代币铸造账户
                    AccountMeta(TOKEN_PROGRAM_ID, False, False),     # 代币程序
                ],
                program_id=self.program_id,
                data=struct.pack("<BQ", 2, amount_lamports)  # 2表示process_withdrawal指令
            )
            
            transaction.add(withdrawal_instruction)
            
            # 发送交易
            result = self.client.send_transaction(
                transaction,
                opts=TxOpts(skip_preflight=False)
            )
            
            return result["result"]
            
        except Exception as e:
            logging.error(f"处理提现请求失败: {str(e)}")
            raise
    
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

# 创建全局客户端实例
solana_client = SolanaClient() 

def get_solana_client():
    """获取Solana客户端实例"""
    return solana_client 