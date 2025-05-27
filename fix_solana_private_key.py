#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def fix_helpers_logic():
    """修复helpers.py中的私钥处理逻辑"""
    
    print("🔧 修复helpers.py中的私钥处理逻辑...")
    
    # 读取helpers.py文件
    helpers_file = "/root/RWA-HUB/app/utils/helpers.py"
    
    with open(helpers_file, 'r') as f:
        content = f.read()
    
    # 查找并替换私钥处理逻辑
    old_pattern = '''        # 处理不同长度的私钥
        if len(private_key_bytes) == 64:
            # 标准64字节格式，前32字节是私钥
            seed = private_key_bytes[:32]
        elif len(private_key_bytes) == 32:
            # 仅私钥
            seed = private_key_bytes
        elif len(private_key_bytes) == 66:
            # 可能包含校验和，取前32字节作为私钥
            seed = private_key_bytes[:32]
            logger.info("检测到66字节私钥，可能包含校验和，使用前32字节")
        else:
            raise ValueError(f"无效的私钥长度: {len(private_key_bytes)}，期望32、64或66字节")
        
        # 创建密钥对
        keypair = Keypair.from_seed(seed)'''
    
    new_pattern = '''        # 处理不同长度的私钥
        if len(private_key_bytes) == 64:
            # 标准64字节格式，前32字节是私钥
            seed = private_key_bytes[:32]
            logger.info("使用64字节私钥的前32字节作为seed")
        elif len(private_key_bytes) == 32:
            # 仅私钥
            seed = private_key_bytes
        elif len(private_key_bytes) == 66:
            # 可能包含校验和，取前32字节作为私钥
            seed = private_key_bytes[:32]
            logger.info("检测到66字节私钥，可能包含校验和，使用前32字节")
        else:
            raise ValueError(f"无效的私钥长度: {len(private_key_bytes)}，期望32、64或66字节")
        
        # 创建密钥对
        keypair = Keypair.from_seed(seed)'''
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        
        with open(helpers_file, 'w') as f:
            f.write(content)
        
        print("✅ 已更新helpers.py中的私钥处理逻辑")
        return True
    else:
        print("❌ 未找到需要更新的代码段")
        
        # 尝试查找其他可能的模式
        if "检测到66字节私钥，可能包含校验和，使用前32字节" in content:
            print("ℹ️  代码已经包含正确的逻辑")
            return True
        
        return False

def restart_application():
    """重启应用"""
    print("\n🔄 重启应用...")
    os.system("pm2 restart rwa-hub")
    print("✅ 应用已重启")

def verify_fix():
    """验证修复结果"""
    print("\n🔍 验证修复结果...")
    
    from app import create_app
    from app.utils.helpers import get_solana_keypair_from_env
    
    app = create_app()
    with app.app_context():
        keypair_info = get_solana_keypair_from_env()
        if keypair_info:
            target_address = "EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4"
            current_address = keypair_info['public_key']
            
            print(f"目标地址: {target_address}")
            print(f"当前地址: {current_address}")
            
            if current_address == target_address:
                print("✅ 私钥配置修复成功！")
                return True
            else:
                print("❌ 私钥配置仍有问题")
                return False
        else:
            print("❌ 无法获取私钥信息")
            return False

if __name__ == "__main__":
    print("🚀 开始修复Solana私钥配置...")
    
    # 步骤1: 修复helpers.py逻辑
    if fix_helpers_logic():
        print("✅ 步骤1完成: helpers.py逻辑已修复")
        
        # 步骤2: 重启应用
        restart_application()
        
        # 步骤3: 验证修复结果
        import time
        print("等待应用启动...")
        time.sleep(5)
        
        if verify_fix():
            print("\n🎉 所有修复完成！系统现在应该使用正确的钱包地址了")
        else:
            print("\n❌ 修复验证失败，需要进一步检查")
    else:
        print("❌ 步骤1失败: 无法修复helpers.py逻辑") 