#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def trigger_asset_onchain_by_id(asset_id):
    """通过资产ID触发自动上链操作"""
    
    try:
        from app import create_app
        from app.extensions import db
        from app.models import Asset
        
        app = create_app()
        
        with app.app_context():
            print(f"🔍 查找资产ID: {asset_id}")
            
            # 查找资产
            asset = Asset.query.filter_by(id=asset_id).first()
            
            if not asset:
                print(f"❌ 未找到资产ID: {asset_id}")
                return False
            
            print(f"📋 当前资产状态:")
            print(f"   资产ID: {asset.id}")
            print(f"   资产名称: {asset.name}")
            print(f"   资产状态: {asset.status}")
            print(f"   支付确认: {asset.payment_confirmed}")
            print(f"   部署进行中: {asset.deployment_in_progress}")
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
                
                if balance >= 0.005:  # 降低阈值到0.005 SOL
                    print(f"   ✅ 余额充足，可以进行上链操作")
                else:
                    print(f"   ⚠️  余额不足，建议充值更多SOL")
            except Exception as e:
                print(f"   ⚠️  无法检查余额: {e}")
            
            # 重置资产状态以触发自动上链
            print(f"\n🔧 重置资产状态以触发自动上链...")
            
            # 设置为支付已确认状态，清除部署标志
            asset.payment_confirmed = True
            asset.status = 2  # payment_confirmed状态
            asset.deployment_in_progress = False
            asset.deployment_started_at = None
            asset.error_message = None
            asset.updated_at = datetime.utcnow()
            
            # 提交更改
            db.session.commit()
            
            print(f"✅ 资产状态已重置:")
            print(f"   支付确认: {asset.payment_confirmed}")
            print(f"   资产状态: {asset.status}")
            print(f"   部署进行中: {asset.deployment_in_progress}")
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

def manually_deploy_asset(asset_id):
    """手动部署资产到区块链（降低SOL阈值）"""
    
    try:
        from app import create_app
        from app.extensions import db
        from app.models import Asset
        from app.blockchain.asset_service import AssetService
        
        app = create_app()
        
        with app.app_context():
            print(f"🚀 手动部署资产ID: {asset_id}")
            
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
            
            # 创建资产服务实例
            asset_service = AssetService()
            
            # 临时修改SOL余额检查阈值
            print(f"\n💰 检查SOL余额（降低阈值到0.005）...")
            
            # 获取Solana客户端并检查余额
            from app.blockchain.solana import SolanaClient
            solana_client = SolanaClient()
            
            balance = solana_client.get_balance()
            print(f"   当前余额: {balance} SOL")
            
            if balance < 0.005:
                print(f"   ❌ 余额不足，需要至少0.005 SOL")
                return False
            
            print(f"   ✅ 余额充足，开始部署...")
            
            # 手动调用部署函数，绕过余额检查
            try:
                # 标记开始部署
                asset.deployment_in_progress = True
                asset.deployment_started_at = datetime.utcnow()
                asset.error_message = None
                db.session.commit()
                
                print(f"🔧 开始创建SPL代币...")
                
                # 直接调用Solana客户端创建代币
                result = solana_client.create_spl_token(
                    asset_name=asset.name,
                    token_symbol=asset.token_symbol,
                    token_supply=asset.token_supply,
                    decimals=9
                )
                
                if result and result.get('success'):
                    # 更新资产信息
                    asset.token_address = result.get('mint_address')
                    asset.deployment_tx_hash = result.get('transaction_hash')
                    asset.status = 3  # deployed状态
                    asset.deployment_in_progress = False
                    asset.blockchain_details = str(result)
                    asset.updated_at = datetime.utcnow()
                    
                    db.session.commit()
                    
                    print(f"✅ 资产部署成功!")
                    print(f"   代币地址: {asset.token_address}")
                    print(f"   交易哈希: {asset.deployment_tx_hash}")
                    
                    return True
                else:
                    # 部署失败
                    error_msg = result.get('error', '未知错误') if result else '创建代币失败'
                    asset.error_message = error_msg
                    asset.deployment_in_progress = False
                    asset.updated_at = datetime.utcnow()
                    db.session.commit()
                    
                    print(f"❌ 资产部署失败: {error_msg}")
                    return False
                    
            except Exception as deploy_e:
                # 部署异常
                asset.error_message = str(deploy_e)
                asset.deployment_in_progress = False
                asset.updated_at = datetime.utcnow()
                db.session.commit()
                
                print(f"❌ 部署过程异常: {deploy_e}")
                return False
            
    except Exception as e:
        print(f"❌ 手动部署失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_system_status():
    """检查系统状态"""
    
    try:
        from app import create_app
        from app.extensions import db
        from app.models import Asset
        
        app = create_app()
        
        with app.app_context():
            print(f"\n📊 系统状态检查:")
            print("=" * 50)
            
            # 统计各状态的资产数量
            total_assets = Asset.query.count()
            confirmed_assets = Asset.query.filter_by(payment_confirmed=True).count()
            deploying_assets = Asset.query.filter_by(deployment_in_progress=True).count()
            deployed_assets = Asset.query.filter_by(status=3).count()
            
            print(f"   总资产数: {total_assets}")
            print(f"   支付确认: {confirmed_assets}")
            print(f"   部署中: {deploying_assets}")
            print(f"   已部署: {deployed_assets}")
            
            # 显示最近的资产
            recent_assets = Asset.query.order_by(Asset.updated_at.desc()).limit(5).all()
            
            if recent_assets:
                print(f"\n📋 最近的资产:")
                for asset in recent_assets:
                    print(f"   • ID:{asset.id} - {asset.name[:30]}... - 状态:{asset.status} - 支付:{asset.payment_confirmed}")
            
            return True
            
    except Exception as e:
        print(f"❌ 检查系统状态失败: {e}")
        return False

def main():
    """主函数"""
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python trigger_asset_onchain_fixed.py <asset_id>          # 重置状态触发自动上链")
        print("  python trigger_asset_onchain_fixed.py <asset_id> manual   # 手动部署（降低SOL阈值）")
        print("  python trigger_asset_onchain_fixed.py status              # 检查系统状态")
        print("示例:")
        print("  python trigger_asset_onchain_fixed.py 28")
        print("  python trigger_asset_onchain_fixed.py 28 manual")
        sys.exit(1)
    
    if sys.argv[1] == "status":
        print("🔍 检查系统状态")
        print("=" * 50)
        check_system_status()
        return
    
    asset_id = int(sys.argv[1])
    manual_mode = len(sys.argv) > 2 and sys.argv[2] == "manual"
    
    print("🚀 触发资产上链操作")
    print("=" * 50)
    
    # 1. 检查系统状态
    check_system_status()
    
    # 2. 触发指定资产上链
    if manual_mode:
        print(f"\n🔧 手动部署模式（降低SOL阈值）")
        success = manually_deploy_asset(asset_id)
    else:
        print(f"\n🔄 自动上链模式")
        success = trigger_asset_onchain_by_id(asset_id)
    
    if success:
        print(f"\n✅ 成功处理资产 {asset_id}")
        if not manual_mode:
            print(f"💡 请等待1-5分钟，系统将自动处理上链")
        print(f"📝 可以通过日志或管理界面查看进度")
    else:
        print(f"\n❌ 处理资产 {asset_id} 失败")

if __name__ == "__main__":
    main() 