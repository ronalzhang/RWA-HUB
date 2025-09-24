from typing import Dict, Any, Optional, List, Union
import requests
import json
from .types import TxOpts
import base64
import logging

class Client:
    """Client to interact with the Solana JSON RPC API."""
    
    def __init__(self, endpoint: str):
        """Initialize client."""
        self.endpoint = endpoint
        self.session = requests.Session()
    
    def _make_request(self, method: str, params: List[Any] = None) -> Dict[str, Any]:
        """Make a request to the RPC endpoint."""
        logger = logging.getLogger(__name__)
        
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params:
            data["params"] = params
        
        # 始终尝试发送真实的RPC请求
        try:
            logger.info(f"发送Solana RPC请求: {method} 到 {self.endpoint}")
            # 安全的参数日志记录，避免JSON序列化错误
            if params:
                try:
                    logger.debug(f"请求参数: {json.dumps(params)}")
                except (TypeError, ValueError):
                    logger.debug(f"请求参数: {params} (无法JSON序列化)")
            else:
                logger.debug("请求参数: None")
            
            response = self.session.post(self.endpoint, json=data, timeout=30)
            
            # 检查HTTP响应状态
            if response.status_code != 200:
                logger.error(f"Solana RPC请求失败，HTTP状态码: {response.status_code}")
                return {"error": {"message": f"HTTP错误: {response.status_code}", "status_code": response.status_code}}
            
            # 解析JSON响应
            result = response.json()
            logger.debug(f"RPC响应: {json.dumps(result)}")
            
            # 检查是否有RPC错误
            if "error" in result:
                logger.error(f"Solana RPC返回错误: {result['error']}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"发送Solana RPC请求时发生网络错误: {str(e)}")
            return {"error": {"message": f"网络错误: {str(e)}"}}
        except json.JSONDecodeError as e:
            logger.error(f"解析Solana RPC响应时发生JSON解析错误: {str(e)}")
            return {"error": {"message": f"JSON解析错误: {str(e)}"}}
        except Exception as e:
            logger.error(f"处理Solana RPC请求时发生未知错误: {str(e)}")
            return {"error": {"message": f"未知错误: {str(e)}"}}
    
    def get_account_info(self, pubkey: str, commitment: Optional[str] = None) -> Dict[str, Any]:
        """Get account info."""
        # 确保pubkey是字符串，防止Pubkey对象序列化错误
        pubkey_str = str(pubkey) if hasattr(pubkey, '__str__') else pubkey
        params = [pubkey_str]
        if commitment:
            params.append({"commitment": commitment})

        return self._make_request("getAccountInfo", params)
    
    def send_transaction(self, transaction, opts: Optional[TxOpts] = None) -> Dict[str, Any]:
        """Send a transaction."""
        tx_data = base64.b64encode(transaction.serialize()).decode('ascii')
        params = [tx_data]
        
        if opts:
            config = {}
            if opts.skip_preflight:
                config["skipPreflight"] = opts.skip_preflight
            if opts.preflight_commitment:
                config["preflightCommitment"] = opts.preflight_commitment
            if opts.commitment:
                config["commitment"] = opts.commitment
            if config:
                params.append(config)
        
        return self._make_request("sendTransaction", params)
    
    def get_balance(self, pubkey: str, commitment: Optional[str] = None) -> Dict[str, Any]:
        """Get balance for a public key."""
        params = [pubkey]
        if commitment:
            params.append({"commitment": commitment})
        
        return self._make_request("getBalance", params)
    
    def get_slot(self, commitment: Optional[str] = None) -> Dict[str, Any]:
        """Get current slot."""
        params = []
        if commitment:
            params.append({"commitment": commitment})
        
        return self._make_request("getSlot", params)
    
    def get_recent_blockhash(self, commitment: Optional[str] = None) -> Dict[str, Any]:
        """Get recent blockhash."""
        params = []
        if commitment:
            params.append({"commitment": commitment})
        
        return self._make_request("getRecentBlockhash", params)
    
    def get_transaction(self, signature: str, commitment: Optional[str] = None) -> Dict[str, Any]:
        """Get transaction details."""
        params = [signature]
        if commitment:
            params.append({"commitment": commitment})
        
        return self._make_request("getTransaction", params)
    
    def get_transaction_count(self, commitment: Optional[str] = None) -> Dict[str, Any]:
        """Get transaction count."""
        params = []
        if commitment:
            params.append({"commitment": commitment})
        
        return self._make_request("getTransactionCount", params)
    
    def send_raw_transaction(self, raw_transaction: bytes, opts: Optional[TxOpts] = None) -> Dict[str, Any]:
        """
        发送已签名的原始交易数据
        
        Args:
            raw_transaction: 已签名的交易字节数据
            opts: 可选的交易选项
            
        Returns:
            Dict包含交易结果
        """
        # 将原始交易数据编码为base64格式
        tx_data = base64.b64encode(raw_transaction).decode('ascii')
        params = [tx_data]
        
        if opts:
            config = {}
            if opts.skip_preflight:
                config["skipPreflight"] = opts.skip_preflight
            if opts.preflight_commitment:
                config["preflightCommitment"] = opts.preflight_commitment
            if opts.commitment:
                config["commitment"] = opts.commitment
            if config:
                params.append(config)
        
        return self._make_request("sendTransaction", params)
    
    def get_signature_statuses(self, signatures: List[str], commitment: str) -> Dict[str, Any]:
        """获取交易签名状态"""
        return self._make_request("getSignatureStatuses", [signatures, {"commitment": commitment}]) 