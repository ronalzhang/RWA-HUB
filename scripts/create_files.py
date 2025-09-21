import os

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created: {path}")

# 智能合约
ASSET_TOKEN = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract AssetToken is ERC20, Ownable {
    constructor(
        string memory name,
        string memory symbol,
        uint256 totalSupply,
        address owner
    ) ERC20(name, symbol) {
        _mint(owner, totalSupply);
        _transferOwnership(owner);
    }
}'''

ASSET_FACTORY = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./AssetToken.sol";

contract AssetFactory {
    event TokenCreated(address tokenAddress, string name, string symbol, uint256 totalSupply, address owner);
    
    function createAssetToken(
        string memory name,
        string memory symbol,
        uint256 totalSupply,
        address owner
    ) public returns (address) {
        AssetToken token = new AssetToken(name, symbol, totalSupply, owner);
        emit TokenCreated(address(token), name, symbol, totalSupply, owner);
        return address(token);
    }
}'''

# 区块链客户端
BLOCKCHAIN_CLIENT = '''from web3 import Web3
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
        }'''

# 编译脚本
COMPILE_SCRIPT = '''from solcx import compile_standard, install_solc
import json
import os

def compile_contracts():
    # 安装solc编译器
    install_solc("0.8.0")
    
    # 编译AssetToken合约
    with open("contracts/solidity/AssetToken.sol", "r") as f:
        token_source = f.read()
    
    # 编译AssetFactory合约
    with open("contracts/solidity/AssetFactory.sol", "r") as f:
        factory_source = f.read()
    
    # 编译配置
    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {
                "AssetToken.sol": {"content": token_source},
                "AssetFactory.sol": {"content": factory_source}
            },
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                    }
                }
            }
        },
        solc_version="0.8.0"
    )
    
    # 创建build目录
    os.makedirs("contracts/build", exist_ok=True)
    
    # 保存编译结果
    with open("contracts/build/AssetToken.json", "w") as f:
        json.dump({
            "abi": compiled_sol["contracts"]["AssetToken.sol"]["AssetToken"]["abi"],
            "bytecode": compiled_sol["contracts"]["AssetToken.sol"]["AssetToken"]["evm"]["bytecode"]["object"]
        }, f, indent=2)
    
    with open("contracts/build/AssetFactory.json", "w") as f:
        json.dump({
            "abi": compiled_sol["contracts"]["AssetFactory.sol"]["AssetFactory"]["abi"],
            "bytecode": compiled_sol["contracts"]["AssetFactory.sol"]["AssetFactory"]["evm"]["bytecode"]["object"]
        }, f, indent=2)

if __name__ == "__main__":
    compile_contracts()'''

def main():
    # 创建智能合约
    write_file('contracts/solidity/AssetToken.sol', ASSET_TOKEN)
    write_file('contracts/solidity/AssetFactory.sol', ASSET_FACTORY)
    
    # 创建区块链客户端
    write_file('app/blockchain/client.py', BLOCKCHAIN_CLIENT)
    write_file('app/blockchain/__init__.py', '')
    
    # 创建编译脚本
    write_file('scripts/compile_contracts.py', COMPILE_SCRIPT)

if __name__ == '__main__':
    main() 