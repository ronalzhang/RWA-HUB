#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
from datetime import datetime

def final_mint_fix():
    """最终修复：添加mint_to方法"""
    
    solana_file = "app/blockchain/solana.py"
    backup_file = f"{solana_file}.backup_mint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # 备份原文件
        shutil.copy2(solana_file, backup_file)
        print(f"✅ 已备份原文件到: {backup_file}")
        
        # 读取文件内容
        with open(solana_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 在MockToken类中添加mint_to方法
        old_class = '''                def create_account(self, **kwargs):
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
        
        new_class = '''                def create_account(self, **kwargs):
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
                    return account_address
                    
                def mint_to(self, **kwargs):
                    """模拟铸造代币到账户"""
                    import base58
                    import hashlib
                    import time
                    tx_seed = f"{self.pubkey}_mint_{int(time.time())}".encode()
                    tx_hash = base58.b58encode(hashlib.sha256(tx_seed).digest()).decode()
                    logger.info(f"模拟铸造代币交易: {tx_hash}")
                    return tx_hash'''
        
        if old_class in content:
            content = content.replace(old_class, new_class)
            print("✅ 已添加mint_to方法到MockToken类")
        else:
            print("⚠️  未找到需要修复的MockToken类")
        
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
    print("🔧 最终修复：添加mint_to方法")
    print("=" * 40)
    
    success = final_mint_fix()
    
    if success:
        print("\n🎉 修复成功！")
        print("🔄 请重启应用: pm2 restart rwa-hub")
    else:
        print("\n❌ 修复失败！") 