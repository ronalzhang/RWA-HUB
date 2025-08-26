#!/usr/bin/env python3
"""
更新服务器环境变量文件
"""

import os
import re

def update_env_file():
    """更新.env文件中的配置"""
    env_file_path = "/root/RWA-HUB/app/.env"
    
    try:
        # 读取现有的.env文件
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = ""
        
        # 更新SOLANA_RPC_URL
        helius_rpc_url = "https://mainnet.helius-rpc.com/?api-key=edbb3e74-772d-4c65-a430-5c89f7ad02ea"
        
        if 'SOLANA_RPC_URL=' in content:
            # 替换现有的SOLANA_RPC_URL
            content = re.sub(
                r'SOLANA_RPC_URL=.*',
                f'SOLANA_RPC_URL={helius_rpc_url}',
                content
            )
            print("✅ 已更新现有的SOLANA_RPC_URL配置")
        else:
            # 添加新的SOLANA_RPC_URL配置
            content += f"\n# Solana配置\nSOLANA_RPC_URL={helius_rpc_url}\n"
            print("✅ 已添加SOLANA_RPC_URL配置")
        
        # 添加加密密钥配置（如果不存在）
        if 'CRYPTO_PASSWORD=' not in content:
            content += f"\n# 加密配置\nCRYPTO_PASSWORD=123abc74531\n"
            print("✅ 已添加CRYPTO_PASSWORD配置")
        
        # 写回文件
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已更新环境变量文件: {env_file_path}")
        return True
        
    except Exception as e:
        print(f"❌ 更新环境变量文件时出错: {e}")
        return False

if __name__ == '__main__':
    update_env_file()