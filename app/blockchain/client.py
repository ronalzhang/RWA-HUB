from web3 import Web3
from eth_account import Account
from eth_typing import Address
from typing import Optional
import json
import os

class BlockchainClient:
    def __init__(self, network_url: str, chain_id: int, private_key: Optional[str] = None):
        self.w3 = Web3(Web3.HTTPProvider(network_url))
        self.chain_id = chain_id
        self.account = Account.from_key(private_key) if private_key else None
        
        # 加载合约ABI
        contract_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "contracts")
        with open(os.path.join(contract_dir, "build/AssetToken.json")) as f:
            contract_json = json.load(f)
            self.token_abi = contract_json["abi"]
            self.token_bytecode = contract_json["bytecode"]
        
        with open(os.path.join(contract_dir, "build/AssetFactory.json")) as f:
            contract_json = json.load(f)
            self.factory_abi = contract_json["abi"]
            self.factory_bytecode = contract_json["bytecode"]
    
    def deploy_factory(self) -> Address:
        """部署资产工厂合约"""
        if not self.account:
            raise ValueError("需要私钥来部署合约")
        
        factory = self.w3.eth.contract(abi=self.factory_abi, bytecode=self.factory_bytecode)
        
        # 构建交易
        transaction = factory.constructor().build_transaction({
            "chainId": self.chain_id,
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
        })
        
        # 签名并发送交易
        signed_txn = self.account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # 等待交易确认
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt.contractAddress
    
    def create_asset_token(
        self,
        factory_address: str,
        name: str,
        symbol: str,
        total_supply: int,
        owner: str
    ) -> str:
        """创建资产代币"""
        if not self.account:
            raise ValueError("需要私钥来创建代币")
        
        factory = self.w3.eth.contract(address=factory_address, abi=self.factory_abi)
        
        # 构建交易
        transaction = factory.functions.createAssetToken(
            name,
            symbol,
            total_supply,
            owner
        ).build_transaction({
            "chainId": self.chain_id,
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
        })
        
        # 签名并发送交易
        signed_txn = self.account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # 等待交易确认
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # 获取代币地址
        token_created_event = factory.events.TokenCreated().process_receipt(tx_receipt)[0]
        return token_created_event.args.tokenAddress
    
    def get_token_info(self, token_address: str) -> dict:
        """获取代币信息"""
        token = self.w3.eth.contract(address=token_address, abi=self.token_abi)
        return {
            "name": token.functions.name().call(),
            "symbol": token.functions.symbol().call(),
            "totalSupply": token.functions.totalSupply().call(),
            "owner": token.functions.owner().call()
        }