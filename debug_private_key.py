#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import base58

def debug_private_key():
    """调试私钥长度和解码问题"""
    
    user_private_key = "4btSt2bvXDjv9Ae1egayTvXkdk9LzocRkbVrjdwi1AFhD8HMcka8SqApydDedDiQdZNkh2BU4bd2DtsdV35dFuRN"
    
    print("🔍 调试私钥问题...")
    print(f"原始私钥: {user_private_key}")
    print(f"原始私钥长度: {len(user_private_key)}")
    
    # 解码私钥
    try:
        private_key_bytes = base58.b58decode(user_private_key)
        print(f"解码后字节长度: {len(private_key_bytes)}")
        print(f"解码后字节(hex): {private_key_bytes.hex()}")
        
        # 检查环境变量中的私钥
        env_key = os.environ.get('SOLANA_PRIVATE_KEY')
        if env_key:
            print(f"\n环境变量私钥: {env_key}")
            print(f"环境变量私钥长度: {len(env_key)}")
            
            if env_key != user_private_key:
                print("❌ 环境变量私钥与用户私钥不匹配！")
                
                # 解码环境变量私钥
                try:
                    env_key_bytes = base58.b58decode(env_key)
                    print(f"环境变量解码后字节长度: {len(env_key_bytes)}")
                    print(f"环境变量解码后字节(hex): {env_key_bytes.hex()}")
                except Exception as e:
                    print(f"环境变量私钥解码失败: {e}")
            else:
                print("✅ 环境变量私钥与用户私钥匹配")
        
        # 检查.env文件
        env_file_path = "/root/RWA-HUB/app/.env"
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                if line.startswith('SOLANA_PRIVATE_KEY='):
                    file_key = line.split('=', 1)[1].strip()
                    print(f"\n.env文件私钥: {file_key}")
                    print(f".env文件私钥长度: {len(file_key)}")
                    
                    if file_key != user_private_key:
                        print("❌ .env文件私钥与用户私钥不匹配！")
                        
                        # 解码.env文件私钥
                        try:
                            file_key_bytes = base58.b58decode(file_key)
                            print(f".env文件解码后字节长度: {len(file_key_bytes)}")
                            print(f".env文件解码后字节(hex): {file_key_bytes.hex()}")
                        except Exception as e:
                            print(f".env文件私钥解码失败: {e}")
                    else:
                        print("✅ .env文件私钥与用户私钥匹配")
                    break
        
        # 检查数据库
        from app import create_app
        from app.models.admin import SystemConfig
        
        app = create_app()
        with app.app_context():
            db_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY')
            if db_key:
                print(f"\n数据库私钥: {db_key}")
                print(f"数据库私钥长度: {len(db_key)}")
                
                if db_key != user_private_key:
                    print("❌ 数据库私钥与用户私钥不匹配！")
                    
                    # 解码数据库私钥
                    try:
                        db_key_bytes = base58.b58decode(db_key)
                        print(f"数据库解码后字节长度: {len(db_key_bytes)}")
                        print(f"数据库解码后字节(hex): {db_key_bytes.hex()}")
                    except Exception as e:
                        print(f"数据库私钥解码失败: {e}")
                else:
                    print("✅ 数据库私钥与用户私钥匹配")
        
    except Exception as e:
        print(f"❌ 私钥解码失败: {e}")

def fix_all_keys():
    """修复所有位置的私钥"""
    
    user_private_key = "4btSt2bvXDjv9Ae1egayTvXkdk9LzocRkbVrjdwi1AFhD8HMcka8SqApydDedDiQdZNkh2BU4bd2DtsdV35dFuRN"
    
    print(f"\n🔧 修复所有位置的私钥...")
    
    # 1. 修复环境变量
    os.environ['SOLANA_PRIVATE_KEY'] = user_private_key
    print("✅ 修复环境变量")
    
    # 2. 修复.env文件
    env_file_path = "/root/RWA-HUB/app/.env"
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as f:
            lines = f.readlines()
        
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('SOLANA_PRIVATE_KEY='):
                lines[i] = f'SOLANA_PRIVATE_KEY={user_private_key}\n'
                updated = True
                break
        
        if not updated:
            lines.append(f'SOLANA_PRIVATE_KEY={user_private_key}\n')
        
        with open(env_file_path, 'w') as f:
            f.writelines(lines)
        
        print("✅ 修复.env文件")
    
    # 3. 修复数据库
    from app import create_app
    from app.models.admin import SystemConfig
    
    app = create_app()
    with app.app_context():
        SystemConfig.set_value('SOLANA_PRIVATE_KEY', user_private_key, '正确的Solana私钥')
        print("✅ 修复数据库")
    
    print("✅ 所有位置的私钥已修复")

if __name__ == "__main__":
    debug_private_key()
    
    print(f"\n是否要修复所有位置的私钥？(y/n): ", end="")
    choice = input().strip().lower()
    if choice == 'y':
        fix_all_keys()
        print("\n请重启应用: pm2 restart rwa-hub") 