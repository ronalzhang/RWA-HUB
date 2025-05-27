#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
from datetime import datetime

def backup_config_file():
    """备份当前配置文件"""
    
    config_file = "app/config.py"
    backup_file = f"app/config.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        shutil.copy2(config_file, backup_file)
        print(f"✅ 配置文件已备份到: {backup_file}")
        return backup_file
    except Exception as e:
        print(f"❌ 备份配置文件失败: {e}")
        return None

def update_ssl_config():
    """更新SSL配置"""
    
    config_file = "app/config.py"
    
    try:
        # 读取当前配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🔍 当前配置分析:")
        print("-" * 40)
        
        # 检查当前SSL配置
        if "sslmode=disable" in content:
            print("⚠️  发现不安全的SSL配置: sslmode=disable")
            
            # 替换SSL配置
            updated_content = content.replace(
                "sslmode=disable", 
                "sslmode=require"
            )
            
            # 写入更新后的配置
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print("✅ SSL配置已更新: sslmode=disable → sslmode=require")
            return True
            
        elif "sslmode=require" in content:
            print("✅ SSL配置已经是安全的: sslmode=require")
            return True
            
        elif "sslmode=" in content:
            print("⚠️  发现其他SSL配置，请手动检查")
            return False
            
        else:
            print("⚠️  未找到SSL配置，建议添加SSL设置")
            
            # 查找数据库URI配置行
            lines = content.split('\n')
            updated_lines = []
            
            for line in lines:
                if "SQLALCHEMY_DATABASE_URI" in line and "postgresql://" in line and "?sslmode=" not in line:
                    # 在数据库URI末尾添加SSL配置
                    if line.strip().endswith("'"):
                        # 单引号结尾
                        line = line.replace("'", "?sslmode=require'")
                    elif line.strip().endswith('"'):
                        # 双引号结尾
                        line = line.replace('"', '?sslmode=require"')
                    print(f"✅ 为数据库URI添加SSL配置: {line.strip()}")
                
                updated_lines.append(line)
            
            # 写入更新后的配置
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(updated_lines))
            
            return True
            
    except Exception as e:
        print(f"❌ 更新SSL配置失败: {e}")
        return False

def verify_ssl_config():
    """验证SSL配置"""
    
    config_file = "app/config.py"
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("\n🔍 验证SSL配置:")
        print("-" * 40)
        
        # 检查所有数据库URI配置
        lines = content.split('\n')
        ssl_configs = []
        
        for i, line in enumerate(lines, 1):
            if "SQLALCHEMY_DATABASE_URI" in line and "postgresql://" in line:
                ssl_configs.append({
                    'line_number': i,
                    'content': line.strip(),
                    'has_ssl': 'sslmode=' in line,
                    'ssl_mode': None
                })
                
                if 'sslmode=' in line:
                    # 提取SSL模式
                    ssl_part = line.split('sslmode=')[1]
                    ssl_mode = ssl_part.split('&')[0].split("'")[0].split('"')[0]
                    ssl_configs[-1]['ssl_mode'] = ssl_mode
        
        if not ssl_configs:
            print("⚠️  未找到数据库URI配置")
            return False
        
        all_secure = True
        for config in ssl_configs:
            print(f"\n📋 第{config['line_number']}行:")
            print(f"   {config['content']}")
            
            if not config['has_ssl']:
                print("   ❌ 未配置SSL")
                all_secure = False
            elif config['ssl_mode'] == 'disable':
                print(f"   ❌ SSL已禁用: {config['ssl_mode']}")
                all_secure = False
            elif config['ssl_mode'] in ['require', 'verify-ca', 'verify-full']:
                print(f"   ✅ SSL配置安全: {config['ssl_mode']}")
            else:
                print(f"   ⚠️  SSL配置需要检查: {config['ssl_mode']}")
                all_secure = False
        
        return all_secure
        
    except Exception as e:
        print(f"❌ 验证SSL配置失败: {e}")
        return False

def show_ssl_security_comparison():
    """显示SSL安全对比"""
    
    print("\n🔒 SSL安全级别对比:")
    print("=" * 60)
    
    ssl_levels = [
        ("sslmode=disable", "❌ 最低", "无加密，数据明文传输"),
        ("sslmode=allow", "⚠️  低", "可选加密，向后兼容"),
        ("sslmode=prefer", "⚠️  中", "优先加密，但允许明文"),
        ("sslmode=require", "✅ 高", "强制加密，推荐生产环境"),
        ("sslmode=verify-ca", "✅ 很高", "加密+CA验证"),
        ("sslmode=verify-full", "✅ 最高", "加密+完整证书验证")
    ]
    
    for mode, level, description in ssl_levels:
        print(f"{level:8} {mode:20} {description}")
    
    print(f"\n💡 建议:")
    print(f"   • 生产环境: sslmode=require")
    print(f"   • 高安全环境: sslmode=verify-ca")
    print(f"   • 最高安全: sslmode=verify-full")

def main():
    """主函数"""
    
    print("🔐 数据库SSL配置修复工具")
    print("=" * 60)
    
    # 1. 备份配置文件
    backup_file = backup_config_file()
    if not backup_file:
        print("❌ 无法备份配置文件，停止操作")
        return
    
    # 2. 显示SSL安全对比
    show_ssl_security_comparison()
    
    # 3. 更新SSL配置
    print(f"\n🔧 开始更新SSL配置...")
    success = update_ssl_config()
    
    if not success:
        print("❌ SSL配置更新失败")
        return
    
    # 4. 验证SSL配置
    print(f"\n🔍 验证SSL配置...")
    is_secure = verify_ssl_config()
    
    # 5. 总结
    print(f"\n" + "📋" * 20)
    print(f"SSL配置修复总结")
    print(f"📋" * 20)
    
    if is_secure:
        print(f"✅ SSL配置修复成功！")
        print(f"✅ 数据库连接现在使用加密传输")
        print(f"✅ 安全级别已提升")
    else:
        print(f"⚠️  SSL配置可能需要手动调整")
        print(f"⚠️  请检查配置文件并重新运行")
    
    print(f"\n💡 下一步操作:")
    print(f"   1. 重启应用以应用新配置")
    print(f"   2. 测试数据库连接是否正常")
    print(f"   3. 监控应用运行状态")
    
    if backup_file:
        print(f"\n🔄 如需回滚:")
        print(f"   cp {backup_file} app/config.py")

if __name__ == "__main__":
    main() 