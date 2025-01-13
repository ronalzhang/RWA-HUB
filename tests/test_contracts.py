import pytest
from web3 import Web3
from eth_account import Account
from solcx import install_solc
from app.blockchain.contracts import deploy_contracts, compile_contracts

# 安装solc编译器
install_solc("0.8.0")

@pytest.fixture
def web3():
    """创建Web3测试实例"""
    return Web3(Web3.EthereumTesterProvider())

@pytest.fixture
def test_accounts(web3):
    """创建测试账户"""
    return [web3.eth.account.create() for _ in range(3)]

@pytest.fixture
def contracts(web3, test_accounts):
    """部署测试合约"""
    owner = test_accounts[0]
    contracts = deploy_contracts(web3, owner.address)
    return contracts

def test_compile_contracts():
    """测试合约编译"""
    contracts = compile_contracts()
    assert "AssetFactory" in contracts
    assert "AssetMarket" in contracts
    assert "AssetRegistry" in contracts

def test_deploy_contracts(web3, test_accounts):
    """测试合约部署"""
    owner = test_accounts[0]
    contracts = deploy_contracts(web3, owner.address)
    
    assert "AssetFactory" in contracts
    assert "AssetMarket" in contracts
    assert "AssetRegistry" in contracts
    
    # 验证合约地址
    assert web3.is_address(contracts["AssetFactory"].address)
    assert web3.is_address(contracts["AssetMarket"].address)
    assert web3.is_address(contracts["AssetRegistry"].address)
