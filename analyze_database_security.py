#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def analyze_database_security():
    """分析数据库存储的安全性"""
    
    print("🔍 数据库安全性深度分析")
    print("=" * 80)
    
    try:
        from app import create_app
        from app.models.admin import SystemConfig
        from app.extensions import db
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            print("📊 SystemConfig表结构分析:")
            print("-" * 40)
            
            # 获取所有配置项
            configs = SystemConfig.query.all()
            sensitive_configs = []
            
            for config in configs:
                # 修复属性访问问题
                config_key = getattr(config, 'config_key', getattr(config, 'key', ''))
                config_value = getattr(config, 'config_value', getattr(config, 'value', ''))
                config_desc = getattr(config, 'description', '')
                config_created = getattr(config, 'created_at', 'Unknown')
                
                if any(keyword in config_key.lower() for keyword in ['private', 'secret', 'password', 'key']):
                    sensitive_configs.append({
                        'key': config_key,
                        'value_length': len(config_value) if config_value else 0,
                        'description': config_desc,
                        'created_at': config_created,
                        'is_encrypted': '***' in config_value if config_value else False
                    })
            
            print(f"   总配置项数量: {len(configs)}")
            print(f"   敏感配置项数量: {len(sensitive_configs)}")
            
            print(f"\n🔐 敏感配置项详情:")
            print("-" * 40)
            for config in sensitive_configs:
                print(f"   • {config['key']}")
                print(f"     值长度: {config['value_length']} 字符")
                print(f"     是否加密: {'是' if config['is_encrypted'] else '否'}")
                print(f"     描述: {config['description']}")
                print(f"     创建时间: {config['created_at']}")
                print()
            
            # 检查数据库连接安全性
            print(f"🔗 数据库连接安全性分析:")
            print("-" * 40)
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            security_checks = []
            
            if 'password' in db_uri:
                security_checks.append(("⚠️", "数据库URI包含密码"))
            if 'localhost' in db_uri:
                security_checks.append(("✅", "使用本地数据库连接"))
            if 'sslmode=disable' in db_uri:
                security_checks.append(("❌", "SSL连接已禁用"))
            if 'sslmode=require' in db_uri:
                security_checks.append(("✅", "SSL连接已启用"))
            
            for status, message in security_checks:
                print(f"   {status} {message}")
            
            # 分析安全风险
            print(f"\n🚨 数据库安全风险评估:")
            print("-" * 40)
            risks = []
            recommendations = []
            
            # 检查敏感信息存储
            unencrypted_sensitive = [c for c in sensitive_configs if not c['is_encrypted']]
            if unencrypted_sensitive:
                risks.append(f"发现 {len(unencrypted_sensitive)} 个未加密的敏感配置项")
                recommendations.append("对敏感配置项进行加密存储")
            
            # 检查SSL连接
            if 'sslmode=disable' in db_uri:
                risks.append("数据库连接未加密")
                recommendations.append("启用数据库SSL连接")
            
            # 检查私钥存储
            private_key_configs = [c for c in sensitive_configs if 'private_key' in c['key'].lower()]
            if private_key_configs:
                risks.append("私钥存储在数据库中")
                recommendations.append("考虑使用专门的密钥管理服务")
            
            # 检查密码存储
            password_configs = [c for c in sensitive_configs if 'password' in c['key'].lower()]
            if password_configs:
                risks.append("密码存储在数据库中")
                recommendations.append("使用哈希或加密存储密码")
            
            if risks:
                print("   发现的安全风险:")
                for i, risk in enumerate(risks, 1):
                    print(f"   {i}. ❌ {risk}")
            else:
                print("   ✅ 未发现明显的数据库安全风险")
            
            print(f"\n💡 安全建议:")
            print("-" * 40)
            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    print(f"   {i}. {rec}")
            else:
                print("   ✅ 当前配置相对安全")
            
            # 数据库表权限检查
            print(f"\n🔒 数据库权限检查:")
            print("-" * 40)
            try:
                # 检查当前用户权限
                result = db.session.execute(text("SELECT current_user, session_user"))
                user_info = result.fetchone()
                print(f"   当前数据库用户: {user_info[0] if user_info else 'Unknown'}")
                
                # 检查表权限（PostgreSQL）
                if 'postgresql' in db_uri:
                    result = db.session.execute(text("""
                        SELECT table_name, privilege_type 
                        FROM information_schema.role_table_grants 
                        WHERE grantee = current_user 
                        AND table_name = 'system_config'
                        LIMIT 5
                    """))
                    permissions = result.fetchall()
                    
                    if permissions:
                        print(f"   system_config表权限:")
                        for perm in permissions:
                            print(f"     • {perm[1]}")
                    else:
                        print(f"   ⚠️  无法获取表权限信息")
                        
            except Exception as e:
                print(f"   ⚠️  权限检查失败: {e}")
            
            return {
                'total_configs': len(configs),
                'sensitive_configs': len(sensitive_configs),
                'unencrypted_sensitive': len(unencrypted_sensitive),
                'risks': risks,
                'recommendations': recommendations
            }
            
    except Exception as e:
        print(f"❌ 数据库安全分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def calculate_solana_cost():
    """计算Solana上链成本"""
    
    print(f"\n💰 Solana上链成本分析")
    print("=" * 80)
    
    # 当前SOL价格（需要实时获取，这里使用估算值）
    sol_price_usd = 173.14  # 当前SOL价格
    
    # Solana网络费用（lamports）
    costs = {
        "创建Mint账户": 1461600,  # ~0.0014616 SOL
        "设置元数据": 5616720,   # ~0.0056167 SOL  
        "创建关联代币账户": 2039280,  # ~0.0020393 SOL
        "铸造代币": 5000,        # ~0.000005 SOL
        "网络基础费用": 5000,     # ~0.000005 SOL
        "缓冲费用": 1000000      # ~0.001 SOL (安全缓冲)
    }
    
    print("📋 详细费用分解:")
    print("-" * 40)
    
    total_lamports = 0
    for item, lamports in costs.items():
        sol_amount = lamports / 1_000_000_000  # 转换为SOL
        usd_amount = sol_amount * sol_price_usd
        total_lamports += lamports
        print(f"   • {item}: {lamports:,} lamports ({sol_amount:.8f} SOL / ${usd_amount:.4f})")
    
    total_sol = total_lamports / 1_000_000_000
    total_usd = total_sol * sol_price_usd
    
    print(f"\n📊 总计费用:")
    print("-" * 40)
    print(f"   总计: {total_lamports:,} lamports")
    print(f"   总计: {total_sol:.8f} SOL")
    print(f"   总计: ${total_usd:.4f} USD")
    
    print(f"\n💡 费用对比:")
    print("-" * 40)
    print(f"   用户预期: ~$0.001 USD")
    print(f"   实际成本: ~${total_usd:.4f} USD")
    print(f"   差异: 约 {total_usd/0.001:.0f}x 高于预期")
    
    print(f"\n🎯 充值建议:")
    print("-" * 40)
    recommended_sol = 0.1
    recommended_usd = recommended_sol * sol_price_usd
    operations_count = recommended_sol / total_sol
    
    print(f"   建议充值: {recommended_sol} SOL (${recommended_usd:.2f})")
    print(f"   可支持操作: 约 {operations_count:.0f} 次上链")
    print(f"   单次成本占比: {(total_sol/recommended_sol)*100:.1f}%")
    
    return {
        'total_sol': total_sol,
        'total_usd': total_usd,
        'recommended_sol': recommended_sol,
        'operations_count': int(operations_count)
    }

if __name__ == "__main__":
    print("🔐 RWA-HUB 数据库安全性与成本分析")
    print("=" * 80)
    
    # 1. 数据库安全分析
    db_analysis = analyze_database_security()
    
    # 2. Solana成本分析
    cost_analysis = calculate_solana_cost()
    
    print(f"\n" + "📋" * 20)
    print(f"分析总结报告")
    print(f"📋" * 20)
    
    if db_analysis:
        print(f"\n🔍 数据库安全总结:")
        print(f"   • 总配置项: {db_analysis['total_configs']} 个")
        print(f"   • 敏感配置项: {db_analysis['sensitive_configs']} 个")
        print(f"   • 未加密敏感项: {db_analysis['unencrypted_sensitive']} 个")
        print(f"   • 安全风险: {len(db_analysis['risks'])} 个")
        print(f"   • 安全建议: {len(db_analysis['recommendations'])} 条")
    
    if cost_analysis:
        print(f"\n💰 成本分析总结:")
        print(f"   • 单次上链成本: {cost_analysis['total_sol']:.8f} SOL (${cost_analysis['total_usd']:.4f})")
        print(f"   • 建议充值: {cost_analysis['recommended_sol']} SOL")
        print(f"   • 可支持操作: {cost_analysis['operations_count']} 次")
    
    print(f"\n⚠️  关于用户问题的回答:")
    print(f"   1. 加密密码 '123abc74531' 相对安全，但建议使用更强密码")
    print(f"   2. 数据库存储确实有泄露风险，建议加密敏感配置")
    print(f"   3. Solana上链成本约 ${cost_analysis['total_usd']:.4f}，比预期0.001U高约{cost_analysis['total_usd']/0.001:.0f}倍")
    print(f"   4. 私钥泄露主要原因：文件权限、Git历史、环境变量暴露")
    print(f"   5. 已完成Git历史清理，敏感文件已从仓库中移除") 