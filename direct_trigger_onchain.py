#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def direct_trigger_asset_onchain(asset_id):
    """直接触发资产上链，不做任何余额检查"""
    
    try:
        from app import create_app
        from app.extensions import db
        from app.models import Asset
        
        app = create_app()
        
        with app.app_context():
            print(f"🚀 直接触发资产{asset_id}上链")
            print("=" * 50)
            
            # 查找资产
            asset = Asset.query.filter_by(id=asset_id).first()
            
            if not asset:
                print(f"❌ 未找到资产ID: {asset_id}")
                return False
            
            print(f"📋 资产信息:")
            print(f"   ID: {asset.id}")
            print(f"   名称: {asset.name}")
            print(f"   当前状态: {asset.status}")
            print(f"   支付确认: {asset.payment_confirmed}")
            print(f"   部署进行中: {asset.deployment_in_progress}")
            
            # 直接重置状态触发自动上链
            print(f"\n🔧 重置资产状态以触发自动上链...")
            
            asset.payment_confirmed = True
            asset.status = 2  # payment_confirmed状态
            asset.deployment_in_progress = False
            asset.deployment_started_at = None
            asset.error_message = None
            asset.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            print(f"✅ 资产状态已重置:")
            print(f"   支付确认: {asset.payment_confirmed}")
            print(f"   资产状态: {asset.status}")
            print(f"   部署进行中: {asset.deployment_in_progress}")
            
            # 手动触发自动监控任务
            print(f"\n🚀 手动触发自动监控任务...")
            
            try:
                from app.tasks import auto_monitor_pending_payments
                auto_monitor_pending_payments()
                print(f"✅ 自动监控任务已执行")
            except Exception as task_e:
                print(f"⚠️  自动监控任务执行异常: {task_e}")
                print(f"💡 系统将在下次定时检查时自动处理")
            
            # 再次检查资产状态
            print(f"\n🔍 检查处理结果...")
            asset = Asset.query.filter_by(id=asset_id).first()
            
            print(f"📋 处理后状态:")
            print(f"   状态: {asset.status}")
            print(f"   部署进行中: {asset.deployment_in_progress}")
            print(f"   代币地址: {asset.token_address}")
            print(f"   交易哈希: {asset.deployment_tx_hash}")
            print(f"   错误信息: {asset.error_message}")
            print(f"   更新时间: {asset.updated_at}")
            
            if asset.token_address:
                print(f"\n🎉 上链成功！")
                print(f"   代币地址: {asset.token_address}")
                if asset.deployment_tx_hash:
                    print(f"   交易哈希: {asset.deployment_tx_hash}")
                return True
            elif asset.error_message:
                print(f"\n❌ 上链失败: {asset.error_message}")
                return False
            else:
                print(f"\n⏳ 上链处理中，请稍后查看结果")
                return True
            
    except Exception as e:
        print(f"❌ 触发上链失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def manual_deploy_asset(asset_id):
    """手动部署资产（直接调用部署函数）"""
    
    try:
        from app import create_app
        from app.extensions import db
        from app.models import Asset
        from app.blockchain.asset_service import AssetService
        
        app = create_app()
        
        with app.app_context():
            print(f"🔧 手动部署资产{asset_id}")
            print("=" * 50)
            
            # 查找资产
            asset = Asset.query.filter_by(id=asset_id).first()
            
            if not asset:
                print(f"❌ 未找到资产ID: {asset_id}")
                return False
            
            print(f"📋 资产信息:")
            print(f"   ID: {asset.id}")
            print(f"   名称: {asset.name}")
            print(f"   代币符号: {asset.token_symbol}")
            print(f"   代币供应量: {asset.token_supply}")
            
            # 创建资产服务
            asset_service = AssetService()
            
            print(f"\n🚀 开始部署到区块链...")
            
            try:
                # 直接调用部署函数
                result = asset_service.deploy_asset_to_blockchain(asset)
                
                if result:
                    print(f"✅ 部署成功!")
                    
                    # 重新查询最新状态
                    asset = Asset.query.filter_by(id=asset_id).first()
                    print(f"📋 部署结果:")
                    print(f"   状态: {asset.status}")
                    print(f"   代币地址: {asset.token_address}")
                    print(f"   交易哈希: {asset.deployment_tx_hash}")
                    print(f"   区块链详情: {asset.blockchain_details}")
                    
                    return True
                else:
                    print(f"❌ 部署失败")
                    asset = Asset.query.filter_by(id=asset_id).first()
                    if asset.error_message:
                        print(f"   错误信息: {asset.error_message}")
                    return False
                    
            except Exception as deploy_e:
                print(f"❌ 部署异常: {deploy_e}")
                return False
            
    except Exception as e:
        print(f"❌ 手动部署失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python direct_trigger_onchain.py <asset_id>        # 重置状态触发自动上链")
        print("  python direct_trigger_onchain.py <asset_id> manual # 手动直接部署")
        print("示例:")
        print("  python direct_trigger_onchain.py 28")
        print("  python direct_trigger_onchain.py 28 manual")
        sys.exit(1)
    
    asset_id = int(sys.argv[1])
    manual_mode = len(sys.argv) > 2 and sys.argv[2] == "manual"
    
    if manual_mode:
        print("🔧 手动部署模式")
        success = manual_deploy_asset(asset_id)
    else:
        print("🔄 自动上链模式")
        success = direct_trigger_asset_onchain(asset_id)
    
    if success:
        print(f"\n✅ 资产{asset_id}处理成功")
    else:
        print(f"\n❌ 资产{asset_id}处理失败")

if __name__ == "__main__":
    main() 