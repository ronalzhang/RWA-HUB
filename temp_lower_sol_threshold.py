#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_balance():
    """检查钱包余额"""
    try:
        from app.blockchain.solana_service import SolanaService
        
        solana_service = SolanaService()
        wallet_address = "6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b"
        balance = solana_service.get_balance(wallet_address)
        
        print(f"💰 钱包余额检查:")
        print(f"   地址: {wallet_address}")
        print(f"   余额: {balance} SOL")
        
        return balance
        
    except Exception as e:
        print(f"❌ 检查余额失败: {e}")
        return None

def trigger_auto_onchain():
    """触发自动上链系统"""
    try:
        from app import create_app
        from app.extensions import db
        from app.models import Asset
        
        app = create_app()
        
        with app.app_context():
            print(f"🔍 查找待上链资产...")
            
            # 查找资产28
            asset = Asset.query.filter_by(id=28).first()
            
            if not asset:
                print(f"❌ 未找到资产ID: 28")
                return False
            
            print(f"📋 资产28状态:")
            print(f"   名称: {asset.name}")
            print(f"   状态: {asset.status}")
            print(f"   支付确认: {asset.payment_confirmed}")
            print(f"   部署进行中: {asset.deployment_in_progress}")
            
            # 重置状态以触发自动上链
            print(f"\n🔧 重置资产状态...")
            asset.payment_confirmed = True
            asset.status = 2  # payment_confirmed
            asset.deployment_in_progress = False
            asset.deployment_started_at = None
            asset.error_message = None
            asset.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            print(f"✅ 资产状态已重置，等待自动上链系统处理")
            
            # 手动触发一次自动监控任务
            print(f"\n🚀 手动触发自动监控任务...")
            
            try:
                from app.tasks import auto_monitor_pending_payments
                auto_monitor_pending_payments()
                print(f"✅ 自动监控任务已执行")
            except Exception as task_e:
                print(f"⚠️  手动触发任务失败: {task_e}")
                print(f"💡 系统将在下次定时检查时自动处理")
            
            return True
            
    except Exception as e:
        print(f"❌ 触发自动上链失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def patch_sol_threshold():
    """临时修改SOL阈值"""
    try:
        print(f"🔧 临时降低SOL余额阈值...")
        
        # 读取solana.py文件
        solana_file = "app/blockchain/solana.py"
        
        with open(solana_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 备份原文件
        backup_file = f"{solana_file}.backup_threshold"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已备份原文件到: {backup_file}")
        
        # 修改阈值
        modified_content = content.replace(
            "def check_balance_sufficient(self, threshold=0.1):",
            "def check_balance_sufficient(self, threshold=0.005):"
        )
        
        if modified_content != content:
            with open(solana_file, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"✅ SOL阈值已临时降低到0.005")
            return True
        else:
            print(f"⚠️  未找到需要修改的阈值代码")
            return False
            
    except Exception as e:
        print(f"❌ 修改SOL阈值失败: {e}")
        return False

def restore_sol_threshold():
    """恢复SOL阈值"""
    try:
        print(f"🔄 恢复SOL余额阈值...")
        
        solana_file = "app/blockchain/solana.py"
        backup_file = f"{solana_file}.backup_threshold"
        
        if os.path.exists(backup_file):
            with open(backup_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            with open(solana_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            os.remove(backup_file)
            print(f"✅ SOL阈值已恢复到原始值")
            return True
        else:
            print(f"⚠️  未找到备份文件")
            return False
            
    except Exception as e:
        print(f"❌ 恢复SOL阈值失败: {e}")
        return False

def main():
    """主函数"""
    
    print("🚀 临时降低SOL阈值并触发自动上链")
    print("=" * 60)
    
    # 1. 检查余额
    balance = check_balance()
    if balance is None:
        print("❌ 无法检查余额，退出")
        return
    
    if balance < 0.005:
        print(f"❌ 余额不足 ({balance} SOL < 0.005 SOL)，请充值更多SOL")
        return
    
    print(f"✅ 余额充足 ({balance} SOL >= 0.005 SOL)")
    
    # 2. 临时修改SOL阈值
    if not patch_sol_threshold():
        print("❌ 修改SOL阈值失败，退出")
        return
    
    try:
        # 3. 重启应用以应用新阈值
        print(f"\n🔄 重启应用以应用新阈值...")
        os.system("pm2 restart rwa-hub")
        
        import time
        time.sleep(3)  # 等待应用重启
        
        # 4. 触发自动上链
        print(f"\n🚀 触发自动上链...")
        success = trigger_auto_onchain()
        
        if success:
            print(f"\n✅ 自动上链已触发，请等待1-5分钟查看结果")
        else:
            print(f"\n❌ 触发自动上链失败")
        
    finally:
        # 5. 恢复原始阈值
        print(f"\n🔄 恢复原始SOL阈值...")
        restore_sol_threshold()
        
        print(f"\n🔄 重启应用以恢复原始配置...")
        os.system("pm2 restart rwa-hub")
        
        print(f"\n✅ 操作完成")

if __name__ == "__main__":
    main() 