#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.blockchain.solana import SolanaClient
from app.utils.helpers import get_solana_keypair_from_env

def check_wallet_balance():
    """检查钱包真实余额"""
    
    print("🔍 检查钱包真实余额...")
    
    # 获取钱包信息
    keypair_info = get_solana_keypair_from_env()
    if not keypair_info:
        print("❌ 无法获取钱包信息")
        return
    
    wallet_address = keypair_info['public_key']
    print(f"📍 钱包地址: {wallet_address}")
    
    # 创建Solana客户端
    client = SolanaClient()
    
    try:
        # 获取SOL余额
        sol_balance = client.get_balance()
        lamports = int(sol_balance * 1e9) if sol_balance else 0
        
        print(f"💰 SOL余额: {sol_balance} SOL")
        print(f"💰 余额(lamports): {lamports} lamports")
        
        # 显示余额信息，不进行阈值检查
        print(f"💡 余额信息: {sol_balance} SOL - 将直接尝试上链操作，让真实网络决定是否成功")
        
        # 尝试获取USDC余额（如果有的话）
        print(f"\n🔍 检查USDC余额...")
        # USDC mint地址 (mainnet)
        usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        try:
            usdc_balance = client.get_token_balance(wallet_address, usdc_mint)
            if usdc_balance is not None:
                print(f"💰 USDC余额: {usdc_balance} USDC")
            else:
                print("💰 USDC余额: 0 USDC (或未找到代币账户)")
        except Exception as e:
            print(f"⚠️  无法获取USDC余额: {e}")
        
    except Exception as e:
        print(f"❌ 获取余额失败: {e}")

if __name__ == "__main__":
    check_wallet_balance() 