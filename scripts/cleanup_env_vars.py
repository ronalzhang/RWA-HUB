#!/usr/bin/env python3
"""
清理不需要的环境变量脚本
"""
import os
import subprocess
import sys

def main():
    print("=== 环境变量清理脚本 ===")
    
    # 需要清理的环境变量（这些现在都通过数据库管理）
    vars_to_remove = [
        'PLATFORM_FEE_ADDRESS',
        'ASSET_CREATION_FEE_ADDRESS', 
        'SOLANA_PLATFORM_ADDRESS',
        'SOLANA_FEE_ADDRESS'
    ]
    
    print("检查需要清理的环境变量...")
    
    for var in vars_to_remove:
        value = os.environ.get(var)
        if value:
            print(f"发现环境变量 {var}={value}")
            print(f"建议手动删除: unset {var}")
        else:
            print(f"✓ {var} 未设置")
    
    print("\n=== 保留的环境变量（这些是必需的）===")
    keep_vars = [
        'SOLANA_RPC_URL',
        'SOLANA_USDC_MINT', 
        'SOLANA_PROGRAM_ID',
        'DATABASE_URL',
        'SECRET_KEY'
    ]
    
    for var in keep_vars:
        value = os.environ.get(var)
        if value:
            # 对于敏感信息只显示前几位
            if 'SECRET' in var or 'DATABASE' in var:
                display_value = value[:10] + "..." if len(value) > 10 else value
            else:
                display_value = value
            print(f"✓ {var}={display_value}")
        else:
            print(f"⚠ {var} 未设置（可能需要配置）")
    
    print("\n=== 说明 ===")
    print("1. USDC mint地址是Solana官方固定地址，不需要修改")
    print("2. 平台收款地址现在通过后台系统设置页面管理")
    print("3. 所有支付相关地址都从数据库动态获取")
    print("4. 如果发现旧的环境变量，请手动删除")

if __name__ == "__main__":
    main() 