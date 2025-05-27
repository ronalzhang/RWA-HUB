#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def trigger_asset_onchain(asset_id):
    """触发指定资产的自动上链操作"""
    
    try:
        from app import create_app
        from app.extensions import db
        from app.models import Asset
        
        app = create_app()
        
        with app.app_context():
            print(f"🔍 查找资产: {asset_id}")
            
            # 查找资产
            asset = Asset.query.filter_by(asset_id=asset_id).first()
            
            if not asset:
                print(f"❌ 未找到资产: {asset_id}")
                return False
            
            print(f"📋 当前资产状态:")
            print(f"   资产ID: {asset.asset_id}")
            print(f"   资产状态: {asset.status}")
            print(f"   支付状态: {asset.payment_status}")
            print(f"   上链状态: {asset.onchain_status}")
            print(f"   创建时间: {asset.created_at}")
            print(f"   更新时间: {asset.updated_at}")
            
            # 检查钱包余额
            wallet_address = "6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b"
            print(f"\n💰 检查钱包余额: {wallet_address}")
            
            try:
                from app.blockchain.solana_service import SolanaService
                solana_service = SolanaService()
                balance = solana_service.get_balance(wallet_address)
                print(f"   当前余额: {balance} SOL")
                
                if balance >= 0.005:  # 至少需要0.005 SOL
                    print(f"   ✅ 余额充足，可以进行上链操作")
                else:
                    print(f"   ⚠️  余额不足，建议充值更多SOL")
            except Exception as e:
                print(f"   ⚠️  无法检查余额: {e}")
            
            # 更新资产状态以触发自动上链
            print(f"\n🔧 更新资产状态以触发自动上链...")
            
            # 设置为支付已确认状态
            asset.payment_status = 'confirmed'
            asset.status = 'payment_confirmed'
            asset.onchain_status = 'pending'
            asset.updated_at = datetime.utcnow()
            
            # 提交更改
            db.session.commit()
            
            print(f"✅ 资产状态已更新:")
            print(f"   支付状态: {asset.payment_status}")
            print(f"   资产状态: {asset.status}")
            print(f"   上链状态: {asset.onchain_status}")
            print(f"   更新时间: {asset.updated_at}")
            
            print(f"\n🚀 自动上链系统将在下次检查时处理此资产")
            print(f"   检查间隔: 每5分钟")
            print(f"   预计处理时间: 1-5分钟内")
            
            return True
            
    except Exception as e:
        print(f"❌ 更新资产状态失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_onchain_system_status():
    """检查自动上链系统状态"""
    
    try:
        from app import create_app
        from app.extensions import db
        from app.models import Asset
        
        app = create_app()
        
        with app.app_context():
            print(f"\n📊 自动上链系统状态检查:")
            print("=" * 50)
            
            # 统计各状态的资产数量
            pending_assets = Asset.query.filter_by(onchain_status='pending').count()
            processing_assets = Asset.query.filter_by(onchain_status='processing').count()
            completed_assets = Asset.query.filter_by(onchain_status='completed').count()
            failed_assets = Asset.query.filter_by(onchain_status='failed').count()
            
            print(f"   待上链资产: {pending_assets}")
            print(f"   上链中资产: {processing_assets}")
            print(f"   已完成资产: {completed_assets}")
            print(f"   失败资产: {failed_assets}")
            
            # 显示最近的待处理资产
            recent_pending = Asset.query.filter_by(
                onchain_status='pending'
            ).order_by(Asset.updated_at.desc()).limit(5).all()
            
            if recent_pending:
                print(f"\n📋 最近的待上链资产:")
                for asset in recent_pending:
                    print(f"   • {asset.asset_id} - {asset.status} - {asset.updated_at}")
            
            return True
            
    except Exception as e:
        print(f"❌ 检查系统状态失败: {e}")
        return False

def main():
    """主函数"""
    
    if len(sys.argv) != 2:
        print("使用方法: python trigger_asset_onchain.py <asset_id>")
        print("示例: python trigger_asset_onchain.py RH-203906")
        sys.exit(1)
    
    asset_id = sys.argv[1]
    
    print("🚀 触发资产自动上链操作")
    print("=" * 50)
    
    # 1. 检查系统状态
    check_onchain_system_status()
    
    # 2. 触发指定资产上链
    success = trigger_asset_onchain(asset_id)
    
    if success:
        print(f"\n✅ 成功触发资产 {asset_id} 的自动上链操作")
        print(f"💡 请等待1-5分钟，系统将自动处理上链")
        print(f"📝 可以通过日志或管理界面查看上链进度")
    else:
        print(f"\n❌ 触发资产 {asset_id} 上链操作失败")

if __name__ == "__main__":
    main() 