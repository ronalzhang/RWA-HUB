from solcx import compile_source, install_solc
import json
import os

def compile_contracts():
    """编译合约"""
    # 获取合约源码
    contract_path = os.path.join(os.path.dirname(__file__), "../../contracts/solidity/AssetFactory.sol")
    with open(contract_path, "r") as f:
        source = f.read()

    # 设置编译器版本
    install_solc("0.8.20")

    # 编译合约
    compiled = compile_source(
        source,
        output_values=["abi", "bin"],
        import_remappings=[
            "@openzeppelin/contracts=/Users/godfather/Downloads/program/58HUB/node_modules/@openzeppelin/contracts"
        ]
    )

    return compiled

def deploy_contracts(web3, owner_address):
    """部署合约"""
    # 编译合约
    contracts = compile_contracts()

    # 部署合约
    contract_interface = contracts["<stdin>:AssetFactory"]
    contract = web3.eth.contract(
        abi=contract_interface["abi"],
        bytecode=contract_interface["bin"]
    )

    # 估算gas
    gas_estimate = contract.constructor().estimate_gas()

    # 发送交易
    tx_hash = contract.constructor().transact({
        "from": owner_address,
        "gas": gas_estimate
    })

    # 等待交易被打包
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    return {
        "factory": web3.eth.contract(
            address=tx_receipt.contractAddress,
            abi=contract_interface["abi"]
        )
    }