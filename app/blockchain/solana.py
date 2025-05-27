# 注释原始导入
# from solana.rpc.api import Client as SolanaRpcClient
# from solana.transaction import Transaction
# from solana.publickey import PublicKey
# from solana.keypair import Keypair
# from solana.system_program import transfer, TransferParams
# from solana.rpc.types import TxOpts
# 保留必要的标准库导入
import base64
import json
import os
import time
import asyncio
# from solana.blockhash import Blockhash
import base58  # 添加base58库导入

# 使用我们的兼容层
from app.utils.solana_compat.rpc.api import Client as SolanaRpcClient
from app.utils.solana_compat.transaction import Transaction
from app.utils.solana_compat.publickey import PublicKey
from app.utils.solana_compat.keypair import Keypair
from app.utils.solana_compat.system_program import SystemProgram
from app.utils.solana_compat.rpc.types import TxOpts
# SPL Token 兼容
from app.utils.solana_compat.token import Token, TOKEN_PROGRAM_ID

# 注释SPL导入
# from spl.token.client import Token
# from spl.token.constants import TOKEN_PROGRAM_ID

from app.models.asset import Asset, AssetStatus
from app.models.transaction import Transaction as DBTransaction
from app.utils.helpers import get_solana_keypair_from_env
from app.utils.config import load_config
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
# 导入助记词相关库
from mnemonic import Mnemonic
from bip32utils import BIP32Key
import hashlib
import hmac
# 导入辅助函数
from ._helpers import validate_mnemonic, load_wallet_from_env

logger = logging.getLogger(__name__)

class SolanaClient:
    """
    Solana区块链客户端，用于与Solana网络交互
    处理SPL代币的创建和资产上链操作
    """
    
    def __init__(self, endpoint_url=None, auth_keypair=None, private_key=None, wallet_address=None):
        """
        初始化Solana客户端
        
        Args:
            endpoint_url (str, optional): Solana集群端点URL. 默认为None.
            auth_keypair (str, optional): 密钥对的路径. 默认为None.
            private_key (str, optional): 私钥. 默认为None.
            wallet_address (str, optional): 钱包地址，仅用于只读操作. 默认为None.
        """
        self.config = load_config()
        endpoint_url = endpoint_url or os.environ.get("SOLANA_NETWORK_URL", "https://api.mainnet-beta.solana.com")
        
        # 只使用真实网络模式

        self.client = SolanaRpcClient(endpoint_url)
        self.endpoint = endpoint_url
        auth_method = "none"

        # 如果只提供了wallet_address但没有私钥，则设置公钥但没有私钥（只读模式）
        if wallet_address and not private_key and not auth_keypair:
            try:
                from app.utils.solana_compat.publickey import PublicKey
                self.public_key = PublicKey(wallet_address)
                self.keypair = None
                logger.info(f"使用只读模式初始化Solana客户端，钱包地址: {wallet_address}")
                return
            except Exception as e:
                logger.error(f"无法解析钱包地址: {str(e)}")
                # 继续执行其他初始化步骤

        # 私钥处理逻辑
        private_key_bytes = None  # 初始化变量
        try:
            # 1. 直接使用参数中提供的私钥
            if private_key:
                logger.info("使用直接提供的私钥初始化")
                try:
                    # 尝试base58解码
                    private_key_bytes = base58.b58decode(private_key)
                    # 如果是64字节，取前32字节作为seed
                    if len(private_key_bytes) == 64:
                        private_key_bytes = private_key_bytes[:32]
                    auth_method = "provided_private_key"
                except Exception as e:
                    logger.warning(f"Base58解码失败，尝试Base64解码: {e}")
                    try:
                        # 备用方案：尝试base64解码
                        private_key_bytes = base64.b64decode(private_key)
                        # 如果是64字节，取前32字节作为seed
                        if len(private_key_bytes) == 64:
                            private_key_bytes = private_key_bytes[:32]
                        auth_method = "provided_private_key_base64"
                    except Exception as e2:
                        logger.error(f"无法解码提供的私钥: {e2}")
                        raise ValueError("无效的私钥格式")
            # 2. 如果提供了keypair文件路径
            elif auth_keypair:
                logger.info(f"使用keypair文件初始化: {auth_keypair}")
                with open(auth_keypair, 'r') as f:
                    private_key_bytes = bytes([int(n) for n in json.load(f)])
                    # 如果是64字节，取前32字节作为seed
                    if len(private_key_bytes) == 64:
                        private_key_bytes = private_key_bytes[:32]
                    auth_method = "keypair_file"
            # 3. 尝试从环境变量获取
            else:
                logger.info("尝试从环境变量获取私钥")
                private_key_bytes = None  # 初始化为None
                wallet_info = get_solana_keypair_from_env()
                if wallet_info and 'private_key' in wallet_info:
                    try:
                        # get_solana_keypair_from_env已经返回了base58编码的私钥
                        private_key_str = wallet_info['private_key']
                        private_key_bytes = base58.b58decode(private_key_str)
                        
                        # 验证私钥长度（应该是32字节的seed）
                        if len(private_key_bytes) != 32:
                            logger.error(f"私钥长度错误: {len(private_key_bytes)}，期望32字节")
                            private_key_bytes = None
                        else:
                            auth_method = "env_private_key_from_helpers"
                            
                    except Exception as e:
                        logger.error(f"处理环境变量私钥失败: {e}")
                        private_key_bytes = None
        except Exception as e:
            logger.error(f"初始化Solana客户端失败: {str(e)}")
            self.client = None
        
        # 创建keypair和客户端
        if private_key_bytes:
            try:
                self.keypair = Keypair.from_seed(private_key_bytes)
                self.public_key = self.keypair.public_key
                logger.info(f"Solana服务钱包初始化成功 - 验证方式: {auth_method}")
                logger.info(f"Solana服务钱包地址: {self.public_key}")
            except Exception as e:
                logger.error(f"从私钥创建Keypair失败: {str(e)}")
                self.keypair = None
                self.public_key = None
        else:
            logger.warning("未提供有效的Solana私钥或助记词，客户端仅能查询，无法执行交易")
            self.keypair = None
            self.public_key = None
            
        try:
            self.client = SolanaRpcClient(self.endpoint)
            logger.info("Solana RPC客户端初始化成功")
        except Exception as e:
            logger.error(f"初始化Solana RPC客户端失败: {str(e)}")
            self.client = None
        
    def _derive_private_key_from_mnemonic(self, mnemonic_phrase):
        """
        从助记词派生Solana私钥
        
        Args:
            mnemonic_phrase: 12/24个单词的助记词，用空格分隔
            
        Returns:
            bytes: 私钥字节
        """
        try:
            # 验证助记词有效性
            mnemo = Mnemonic("english")
            if not mnemo.check(mnemonic_phrase):
                raise ValueError("无效的助记词")
                
            # 派生种子
            seed = mnemo.to_seed(mnemonic_phrase, passphrase="")
            
            # 尝试不同的派生路径
            # 1. 尝试Phantom钱包路径: m/44'/501'/0'
            try:
                logger.info("尝试使用Phantom钱包派生路径: m/44'/501'/0'")
                
                # 从种子派生密钥
                root_key = BIP32Key.fromEntropy(seed)
                
                # Phantom钱包路径 m/44'/501'/0'
                purpose = 44
                coin = 501  # Solana的币种类型
                account = 0
                
                # 依次派生
                derived_key = root_key.ChildKey(purpose | 0x80000000)  # 硬化派生
                derived_key = derived_key.ChildKey(coin | 0x80000000)  # 硬化派生
                derived_key = derived_key.ChildKey(account | 0x80000000)  # 硬化派生
                
                # 获取私钥
                private_key_bytes = derived_key.PrivateKey()
                
                # 验证生成的钱包地址
                test_keypair = Keypair.from_secret_key(private_key_bytes)
                test_pubkey = test_keypair.public_key
                logger.info(f"Phantom路径生成的钱包地址: {test_pubkey}")
                
                # 验证是否与预期地址匹配
                expected_prefix = "EeYf"  # 用户钱包地址的前几个字符
                if str(test_pubkey).startswith(expected_prefix):
                    logger.info(f"成功匹配用户Phantom钱包地址: {test_pubkey}")
                    return private_key_bytes
            except Exception as e:
                logger.warning(f"Phantom路径派生尝试失败: {str(e)}")
            
            # 2. 尝试标准Solana路径: m/44'/501'/0'/0'
            try:
                logger.info("尝试使用标准Solana派生路径: m/44'/501'/0'/0'")
                
                # 从种子派生密钥
                root_key = BIP32Key.fromEntropy(seed)
                
                # 标准派生路径为 m/44'/501'/0'/0' (Solana)
                purpose = 44
                coin = 501  # Solana的币种类型
                account = 0
                change = 0
                
                # 依次派生
                derived_key = root_key.ChildKey(purpose | 0x80000000)  # 硬化派生
                derived_key = derived_key.ChildKey(coin | 0x80000000)  # 硬化派生
                derived_key = derived_key.ChildKey(account | 0x80000000)  # 硬化派生
                derived_key = derived_key.ChildKey(change | 0x80000000)  # 硬化派生
                
                # 获取私钥
                private_key_bytes = derived_key.PrivateKey()
                
                # 验证生成的钱包地址
                test_keypair = Keypair.from_secret_key(private_key_bytes)
                test_pubkey = test_keypair.public_key
                logger.info(f"标准路径生成的钱包地址: {test_pubkey}")
                
                # 验证是否与预期地址匹配
                expected_prefix = "EeYf"  # 用户钱包地址的前几个字符
                if str(test_pubkey).startswith(expected_prefix):
                    logger.info(f"成功匹配用户钱包地址: {test_pubkey}")
                    return private_key_bytes
            except Exception as e:
                logger.warning(f"标准路径派生尝试失败: {str(e)}")
            
            # 3. 尝试更多可能的路径
            possible_paths = [
                [44, 501, 0, 0, 0],    # m/44'/501'/0'/0/0
                [44, 501, 0],          # m/44'/501'/0'
                [44, 501],             # m/44'/501'
                [501, 0]               # m/501'/0'
            ]
            
            for path in possible_paths:
                try:
                    # 修复f-string语法错误
                    path_str = "m/"
                    for i, p in enumerate(path):
                        if i > 0:
                            path_str += "/"
                        path_str += str(p)
                        if i < len(path) - 1:
                            path_str += "'"
                    
                    logger.info(f"尝试派生路径: {path_str}")
                    
                    # 从种子派生密钥
                    derived_key = BIP32Key.fromEntropy(seed)
                    
                    # 依次派生
                    for part in path:
                        if part < 0x80000000:  # 非硬化派生
                            derived_key = derived_key.ChildKey(part)
                        else:  # 硬化派生
                            derived_key = derived_key.ChildKey(part | 0x80000000)
                    
                    # 获取私钥
                    private_key_bytes = derived_key.PrivateKey()
                    
                    # 验证生成的钱包地址
                    test_keypair = Keypair.from_secret_key(private_key_bytes)
                    test_pubkey = test_keypair.public_key
                    logger.info(f"路径生成的钱包地址: {test_pubkey}")
                    
                    # 验证是否与预期地址匹配
                    expected_prefix = "EeYf"  # 用户钱包地址的前几个字符
                    if str(test_pubkey).startswith(expected_prefix):
                        logger.info(f"成功匹配用户钱包地址: {test_pubkey}")
                        return private_key_bytes
                except Exception as e:
                    logger.warning(f"派生路径尝试失败: {str(e)}")
            
            # 如果所有路径都没有匹配，返回最标准的路径结果
            logger.warning("未找到匹配用户钱包地址的派生路径，使用标准Solana路径")
            
            # 从种子派生密钥
            root_key = BIP32Key.fromEntropy(seed)
            
            # 标准派生路径为 m/44'/501'/0'/0' (Solana)
            purpose = 44
            coin = 501  # Solana的币种类型
            account = 0
            change = 0
            
            # 依次派生
            derived_key = root_key.ChildKey(purpose | 0x80000000)  # 硬化派生
            derived_key = derived_key.ChildKey(coin | 0x80000000)  # 硬化派生
            derived_key = derived_key.ChildKey(account | 0x80000000)  # 硬化派生
            derived_key = derived_key.ChildKey(change | 0x80000000)  # 硬化派生
            
            # 获取私钥
            private_key_bytes = derived_key.PrivateKey()
            
            logger.info("成功从助记词派生私钥（使用标准路径）")
            return private_key_bytes
            
        except Exception as e:
            logger.error(f"从助记词派生私钥失败: {str(e)}")
            raise ValueError(f"助记词处理错误: {str(e)}")
        
    def get_balance(self):
        """获取服务钱包SOL余额"""
        if not self.public_key:
            raise ValueError("未初始化钱包公钥，无法查询余额")
            

        # 首先尝试主节点
        try:
            logger.info(f"正在获取钱包 {self.public_key} 的SOL余额...")
            balance_resp = self.client.get_balance(str(self.public_key))
            logger.debug(f"余额查询响应: {balance_resp}")
            
            if 'result' in balance_resp and 'value' in balance_resp['result']:
                balance_lamports = balance_resp['result']['value']
                balance_sol = balance_lamports / 10**9  # 将lamports转换为SOL
                logger.info(f"获取到钱包余额: {balance_sol} SOL")
                return balance_sol
        except Exception as e:
            import traceback
            logger.warning(f"主节点获取SOL余额异常: {str(e)}")
            logger.debug(f"主节点异常详情: {traceback.format_exc()}")
            
            # 如果主节点失败，尝试备用节点
            for backup_node in self.backup_nodes:
                try:
                    logger.info(f"尝试使用备用节点: {backup_node}")
                    backup_client = SolanaRpcClient(backup_node)
                    balance_resp = backup_client.get_balance(str(self.public_key))
                    
                    if 'result' in balance_resp and 'value' in balance_resp['result']:
                        balance_lamports = balance_resp['result']['value']
                        balance_sol = balance_lamports / 10**9
                        logger.info(f"从备用节点获取到钱包余额: {balance_sol} SOL")
                        return balance_sol
                except Exception as backup_e:
                    logger.warning(f"备用节点 {backup_node} 获取SOL余额异常: {str(backup_e)}")
                    continue
        
        # 所有节点都失败
        logger.error("所有Solana RPC节点都无法获取余额")
        return None
            
    def check_balance_sufficient(self, threshold=0.1):
        """检查服务钱包余额是否充足"""
        balance = self.get_balance()
        if balance is None:
            return False
            
        is_sufficient = balance >= threshold
        if not is_sufficient:
            logger.warning(f"SOL余额不足! 当前: {balance} SOL, 阈值: {threshold} SOL")
        return is_sufficient
        
    def create_spl_token(self, asset_name, token_symbol, token_supply, decimals=9):
        """
        创建SPL代币并mint指定数量的代币
        
        Args:
            asset_name: 资产名称
            token_symbol: 代币符号
            token_supply: 代币供应量
            decimals: 代币小数位数
            
        Returns:
            dict: 包含代币地址和mint交易ID的字典
        """

        if not self.keypair:
            if self.readonly_mode:
                raise ValueError("钱包处于只读模式，无法创建代币。只读模式仅支持查询操作，不支持交易操作。")
            else:
                raise ValueError("未初始化钱包私钥，无法创建代币")
            
        try:
            logger.info(f"开始创建SPL代币: {asset_name} ({token_symbol})")
            
            # 创建代币
            token = Token.create_mint(
                conn=self.client,
                payer=self.keypair,
                mint_authority=self.public_key,
                decimals=decimals,
                program_id=TOKEN_PROGRAM_ID
            )
            
            logger.info(f"SPL代币创建成功: {token.pubkey}")
            
            # 创建代币账户
            token_account = token.create_account(owner=self.public_key)
            logger.info(f"代币账户创建成功: {token_account}")
            
            # 发行代币
            mint_amount = token_supply * (10 ** decimals)
            mint_tx = token.mint_to(
                dest=token_account,
                mint_authority=self.keypair,
                amount=int(mint_amount)
            )
            
            logger.info(f"代币mint成功，交易ID: {mint_tx}")
            
            return {
                'token_address': str(token.pubkey),
                'token_account': str(token_account),
                'mint_tx': mint_tx,
                'decimals': decimals,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"创建SPL代币失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def deploy_asset(self, asset):
        """
        将资产部署到Solana链上
        
        Args:
            asset: 资产模型对象，包含资产的详细信息
            
        Returns:
            dict: 上链结果
        """
        if not self.keypair:
            raise ValueError("未初始化钱包私钥，无法部署资产")
            
        try:
            logger.info(f"开始部署资产到Solana: ID={asset.id}, 名称={asset.name}")
            
            # 检查余额是否充足
            if not self.check_balance_sufficient():
                return {
                    'success': False,
                    'error': '服务钱包SOL余额不足'
                }
                
            # 创建代币
            token_result = self.create_spl_token(
                asset_name=asset.name,
                token_symbol=asset.token_symbol,
                token_supply=asset.token_supply
            )
            
            if not token_result.get('success', False):
                return token_result
                
            # 记录上链时间和详情
            deployment_details = {
                'deployed_at': datetime.utcnow().isoformat(),
                'token_address': token_result['token_address'],
                'token_account': token_result['token_account'],
                'mint_tx': token_result['mint_tx'],
                'network': self.endpoint,
                'deployed_by': str(self.public_key)
            }
            
            logger.info(f"资产部署成功: {deployment_details}")
            
            return {
                'success': True,
                'token_address': token_result['token_address'],
                'details': deployment_details
            }
            
        except Exception as e:
            logger.error(f"部署资产到Solana失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def get_transaction_status(self, tx_signature):
        """
        获取交易状态
        
        Args:
            tx_signature: 交易签名/ID
            
        Returns:
            str: 交易状态
        """
        try:
            tx_info = self.client.get_transaction(tx_signature)
            if 'result' in tx_info and tx_info['result']:
                return 'confirmed'
            return 'unknown'
        except Exception as e:
            logger.error(f"获取交易状态失败: {str(e)}")
            return 'error' 