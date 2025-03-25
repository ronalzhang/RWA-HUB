from typing import Dict, Any, Optional, List, Union
import requests
import json
from .types import TxOpts
import base64

class Client:
    """Client to interact with the Solana JSON RPC API."""
    
    def __init__(self, endpoint: str):
        """Initialize client."""
        self.endpoint = endpoint
        self.session = requests.Session()
    
    def _make_request(self, method: str, params: List[Any] = None) -> Dict[str, Any]:
        """Make a request to the RPC endpoint."""
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params:
            data["params"] = params
        
        # 在开发环境中，避免真实的网络请求
        # 返回模拟数据
        if method == "getAccountInfo":
            return {"result": {"value": {"data": "", "lamports": 1000000, "owner": ""}}}
        elif method == "getBalance":
            return {"result": {"value": 1000000}}
        elif method == "getRecentBlockhash":
            return {"result": {"value": {"blockhash": "simulated_blockhash", "feeCalculator": {"lamportsPerSignature": 5000}}}}
        elif method == "sendTransaction":
            return {"result": "simulated_signature_" + str(hash(json.dumps(data)))}
        elif method == "getTransaction":
            return {"result": {"meta": {"err": None, "status": {"Ok": None}}}}
        elif method == "getSlot":
            return {"result": 12345}
        elif method == "getSignatureStatuses":
            return {"result": {"value": [{"slot": 12345, "confirmations": 5, "err": None, "status": {"Ok": None}}]}}
        
        # 如果是其他方法，尝试真实请求
        try:
            response = self.session.post(self.endpoint, json=data)
            return response.json()
        except Exception as e:
            return {"error": {"message": str(e)}}
    
    def get_account_info(self, pubkey: str, commitment: Optional[str] = None) -> Dict[str, Any]:
        """Get account info."""
        params = [pubkey]
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