#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
from datetime import datetime

def simple_fix():
    """简化修复MockToken参数问题"""
    
    solana_file = "app/blockchain/solana.py"
    backup_file = f"{solana_file}.backup_simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # 备份原文件
        shutil.copy2(solana_file, backup_file)
        print(f"✅ 已备份原文件到: {backup_file}")
        
        # 读取文件内容
        with open(solana_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复MockToken的create_account方法定义
        old_method = '''                def create_account(self, owner, mint, owner_authority, amount, decimals):
                    """模拟创建代币账户"""
                    import base58
                    import hashlib
                    import time
                    account_seed = f"{mint}_{owner}_{int(time.time())}".encode()
                    account_hash = hashlib.sha256(account_seed).digest()[:32]
                    account_address = base58.b58encode(account_hash).decode()
                    logger.info(f"模拟创建代币账户: {account_address}")
                    return account_address'''
        
        new_method = '''                def create_account(self, **kwargs):
                    """模拟创建代币账户 - 接受任意参数"""
                    import base58
                    import hashlib
                    import time
                    owner = kwargs.get('owner', 'default')
                    mint = kwargs.get('mint', self.pubkey)
                    account_seed = f"{mint}_{owner}_{int(time.time())}".encode()
                    account_hash = hashlib.sha256(account_seed).digest()[:32]
                    account_address = base58.b58encode(account_hash).decode()
                    logger.info(f"模拟创建代币账户: {account_address}")
                    return account_address'''
        
        if old_method in content:
            content = content.replace(old_method, new_method)
            print("✅ 已修复MockToken.create_account方法")
        else:
            print("⚠️  未找到需要修复的create_account方法")
        
        # 写入修复后的内容
        with open(solana_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 修复完成")
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        # 恢复备份
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, solana_file)
            print(f"已恢复备份文件")
        return False

if __name__ == "__main__":
    print("🔧 简化修复MockToken参数问题")
    print("=" * 40)
    
    success = simple_fix()
    
    if success:
        print("\n🎉 修复成功！")
        print("🔄 请重启应用: pm2 restart rwa-hub")
    else:
        print("\n❌ 修复失败！") 