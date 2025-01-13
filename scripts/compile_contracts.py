from solcx import compile_standard, install_solc
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
                "optimizer": {
                    "enabled": True,
                    "runs": 200
                },
                "outputSelection": {
                    "*": {
                        "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                    }
                }
            }
        },
        solc_version="0.8.0",
        allow_paths=["contracts/solidity"]
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
    compile_contracts()