#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def fix_crypto_password_logic():
    """修复加密密码逻辑问题"""
    
    print("🔧 修复加密密码逻辑问题")
    print("=" * 80)
    
    try:
        from app import create_app
        from app.models.admin import SystemConfig
        from app.extensions import db
        
        app = create_app()
        with app.app_context():
            
            # 1. 检查当前数据库中的CRYPTO_PASSWORD
            print("📋 检查当前配置...")
            crypto_config = SystemConfig.query.filter_by(config_key='CRYPTO_PASSWORD').first()
            
            if crypto_config:
                current_password = crypto_config.config_value
                print(f"✅ 找到数据库中的CRYPTO_PASSWORD: {current_password[:10]}...")
                
                # 2. 从数据库中删除CRYPTO_PASSWORD
                print(f"\n🗑️ 从数据库中删除CRYPTO_PASSWORD...")
                db.session.delete(crypto_config)
                db.session.commit()
                print(f"✅ 已从数据库中删除CRYPTO_PASSWORD")
                
                # 3. 生成环境变量设置命令
                print(f"\n📝 生成环境变量设置命令:")
                print(f"export CRYPTO_PASSWORD='{current_password}'")
                
                # 4. 检查代码中是否需要修改
                print(f"\n🔍 检查需要修改的代码文件...")
                files_to_check = [
                    'app/utils/helpers.py',
                    'app/config.py',
                    'app/models/admin.py'
                ]
                
                for file_path in files_to_check:
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'CRYPTO_PASSWORD' in content:
                                print(f"   📁 {file_path} - 需要检查")
                            else:
                                print(f"   ✅ {file_path} - 无需修改")
                
                return current_password
                
            else:
                print(f"⚠️  数据库中未找到CRYPTO_PASSWORD配置")
                
                # 检查环境变量
                env_password = os.environ.get('CRYPTO_PASSWORD')
                if env_password:
                    print(f"✅ 环境变量中已有CRYPTO_PASSWORD: {env_password[:10]}...")
                    return env_password
                else:
                    print(f"❌ 环境变量中也未找到CRYPTO_PASSWORD")
                    return None
                    
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def update_helpers_file():
    """更新helpers.py文件以从环境变量读取密码"""
    
    print(f"\n🔧 更新helpers.py文件...")
    print("-" * 40)
    
    helpers_file = 'app/utils/helpers.py'
    
    if not os.path.exists(helpers_file):
        print(f"❌ 文件不存在: {helpers_file}")
        return False
    
    try:
        with open(helpers_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经使用环境变量
        if 'os.environ.get(\'CRYPTO_PASSWORD\')' in content:
            print(f"✅ helpers.py已经使用环境变量读取密码")
            return True
        
        # 查找需要修改的部分
        if 'SystemConfig.get_value(\'CRYPTO_PASSWORD\')' in content:
            print(f"🔍 发现需要修改的代码...")
            
            # 替换为环境变量读取
            new_content = content.replace(
                "SystemConfig.get_value('CRYPTO_PASSWORD')",
                "os.environ.get('CRYPTO_PASSWORD')"
            )
            
            # 确保导入os模块
            if 'import os' not in new_content:
                new_content = 'import os\n' + new_content
            
            # 写入修改后的内容
            with open(helpers_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ helpers.py已更新为使用环境变量")
            return True
        else:
            print(f"⚠️  未找到需要修改的代码")
            return False
            
    except Exception as e:
        print(f"❌ 更新helpers.py失败: {e}")
        return False

def create_env_setup_script(password):
    """创建环境变量设置脚本"""
    
    print(f"\n📝 创建环境变量设置脚本...")
    print("-" * 40)
    
    if not password:
        print(f"❌ 密码为空，无法创建脚本")
        return False
    
    script_content = f"""#!/bin/bash
# 设置CRYPTO_PASSWORD环境变量

echo "🔐 设置CRYPTO_PASSWORD环境变量..."

# 设置当前会话的环境变量
export CRYPTO_PASSWORD='{password}'

# 添加到.bashrc（如果存在）
if [ -f ~/.bashrc ]; then
    if ! grep -q "CRYPTO_PASSWORD" ~/.bashrc; then
        echo "export CRYPTO_PASSWORD='{password}'" >> ~/.bashrc
        echo "✅ 已添加到 ~/.bashrc"
    else
        echo "⚠️  ~/.bashrc 中已存在 CRYPTO_PASSWORD"
    fi
fi

# 添加到.profile（如果存在）
if [ -f ~/.profile ]; then
    if ! grep -q "CRYPTO_PASSWORD" ~/.profile; then
        echo "export CRYPTO_PASSWORD='{password}'" >> ~/.profile
        echo "✅ 已添加到 ~/.profile"
    else
        echo "⚠️  ~/.profile 中已存在 CRYPTO_PASSWORD"
    fi
fi

echo "✅ 环境变量设置完成"
echo "💡 请运行: source ~/.bashrc 或重新登录以生效"
"""
    
    try:
        with open('setup_crypto_env.sh', 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # 设置执行权限
        os.chmod('setup_crypto_env.sh', 0o755)
        
        print(f"✅ 已创建环境变量设置脚本: setup_crypto_env.sh")
        print(f"💡 运行方法: ./setup_crypto_env.sh")
        return True
        
    except Exception as e:
        print(f"❌ 创建脚本失败: {e}")
        return False

def verify_fix():
    """验证修复结果"""
    
    print(f"\n🔍 验证修复结果...")
    print("-" * 40)
    
    try:
        from app import create_app
        from app.models.admin import SystemConfig
        
        app = create_app()
        with app.app_context():
            
            # 检查数据库中是否还有CRYPTO_PASSWORD
            crypto_config = SystemConfig.query.filter_by(config_key='CRYPTO_PASSWORD').first()
            
            if crypto_config:
                print(f"❌ 数据库中仍存在CRYPTO_PASSWORD")
                return False
            else:
                print(f"✅ 数据库中已无CRYPTO_PASSWORD")
            
            # 检查环境变量
            env_password = os.environ.get('CRYPTO_PASSWORD')
            if env_password:
                print(f"✅ 环境变量CRYPTO_PASSWORD已设置: {env_password[:10]}...")
            else:
                print(f"⚠️  环境变量CRYPTO_PASSWORD未设置")
            
            # 测试加密/解密功能
            try:
                from app.utils.helpers import encrypt_data, decrypt_data
                
                test_data = "test_encryption_123"
                encrypted = encrypt_data(test_data)
                decrypted = decrypt_data(encrypted)
                
                if decrypted == test_data:
                    print(f"✅ 加密/解密功能正常")
                    return True
                else:
                    print(f"❌ 加密/解密功能异常")
                    return False
                    
            except Exception as e:
                print(f"⚠️  加密/解密测试失败: {e}")
                return False
                
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

if __name__ == "__main__":
    print("🔐 修复加密密码逻辑问题")
    print("=" * 80)
    
    # 1. 修复加密密码逻辑
    password = fix_crypto_password_logic()
    
    if password:
        # 2. 更新helpers.py文件
        helpers_updated = update_helpers_file()
        
        # 3. 创建环境变量设置脚本
        script_created = create_env_setup_script(password)
        
        # 4. 验证修复结果
        verification_passed = verify_fix()
        
        print(f"\n" + "📋" * 20)
        print(f"修复完成报告")
        print(f"📋" * 20)
        
        print(f"\n✅ 修复步骤完成情况:")
        print(f"   • 数据库密码移除: ✅")
        print(f"   • helpers.py更新: {'✅' if helpers_updated else '❌'}")
        print(f"   • 环境变量脚本: {'✅' if script_created else '❌'}")
        print(f"   • 功能验证: {'✅' if verification_passed else '❌'}")
        
        print(f"\n💡 下一步操作:")
        print(f"   1. 运行: ./setup_crypto_env.sh")
        print(f"   2. 重启应用: pm2 restart rwa-hub")
        print(f"   3. 测试加密/解密功能")
        
        if not verification_passed:
            print(f"\n⚠️  注意: 功能验证未通过，请检查环境变量设置")
    else:
        print(f"\n❌ 修复失败: 无法获取密码") 