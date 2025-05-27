#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试真实自动上链流程
监控RH-203906资产的自动上链过程
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.asset import Asset, AssetStatus
from app.models.admin import OnchainHistory
from app.blockchain.asset_service import AssetService
from app.extensions import db
import time
import json

def test_auto_onchain(asset_symbol='RH-203906'):
    """测试真实自动上链流程"""
    app = create_app()
    
    with app.app_context():
        try:
            # 查找资产
            asset = Asset.query.filter_by(token_symbol=asset_symbol).first()
            
            if not asset:
                print(f"❌ 未找到{asset_symbol}资产")
                return False
            
            print(f"🎯 开始测试资产 {asset_symbol} 的真实自动上链流程")
            print(f"📋 资产信息: {asset.name} (ID: {asset.id})")
            print(f"当前状态: {asset.status} ({'CONFIRMED' if asset.status == 5 else 'OTHER'})")
            print(f"支付确认: {asset.payment_confirmed}")
            print(f"Token地址: {asset.token_address}")
            print(f"部署进行中: {asset.deployment_in_progress}")
            
            if asset.status != AssetStatus.CONFIRMED.value:
                print(f"❌ 资产状态不正确，应为CONFIRMED(5)，当前为{asset.status}")
                return False
                
            if not asset.payment_confirmed:
                print(f"❌ 资产支付未确认")
                return False
                
            if asset.token_address:
                print(f"❌ 资产已有Token地址，无需重新上链")
                return False
            
            print(f"\n✅ 资产状态正确，开始触发自动上链流程...")
            
            # 初始化AssetService
            asset_service = AssetService()
            
            # 模拟支付确认触发上链
            payment_info = {
                'status': 'confirmed',
                'amount': 100.0,
                'tx_hash': f'test_payment_hash_for_{asset_symbol}',
                'wallet_address': 'test_wallet_for_auto_onchain'
            }
            
            print(f"🚀 触发支付处理流程...")
            result = asset_service.process_asset_payment(asset.id, payment_info)
            
            print(f"📊 支付处理结果: {result}")
            
            if result.get('success'):
                print(f"✅ 支付处理成功，开始监控上链进度...")
                
                # 监控上链进度
                max_wait_time = 300  # 最多等待5分钟
                check_interval = 10  # 每10秒检查一次
                elapsed_time = 0
                
                while elapsed_time < max_wait_time:
                    # 刷新资产状态
                    db.session.refresh(asset)
                    
                    print(f"\n⏰ 检查进度 ({elapsed_time}s):")
                    print(f"  状态: {asset.status}")
                    print(f"  Token地址: {asset.token_address}")
                    print(f"  部署进行中: {asset.deployment_in_progress}")
                    print(f"  部署交易哈希: {asset.deployment_tx_hash}")
                    
                    # 检查上链历史记录
                    history_records = OnchainHistory.query.filter_by(asset_id=asset.id).all()
                    print(f"  上链历史记录: {len(history_records)} 条")
                    for record in history_records:
                        print(f"    - 状态: {record.status}, 触发类型: {record.trigger_type}")
                        if record.transaction_hash:
                            print(f"      交易哈希: {record.transaction_hash}")
                        if record.error_message:
                            print(f"      错误信息: {record.error_message}")
                    
                    # 检查是否完成
                    if asset.status == AssetStatus.ON_CHAIN.value and asset.token_address:
                        print(f"\n🎉 上链成功完成!")
                        print(f"✅ 最终Token地址: {asset.token_address}")
                        print(f"✅ 部署交易哈希: {asset.deployment_tx_hash}")
                        
                        # 验证Token地址是否真实
                        if asset.token_address and not asset.token_address.startswith('So'):
                            print(f"⚠️  Token地址格式可能不是真实的Solana地址")
                        else:
                            print(f"✅ Token地址格式正确")
                            
                        return True
                    
                    elif asset.status == AssetStatus.DEPLOYMENT_FAILED.value:
                        print(f"\n❌ 上链失败!")
                        print(f"错误信息: {getattr(asset, 'error_message', 'Unknown error')}")
                        return False
                    
                    # 等待下次检查
                    time.sleep(check_interval)
                    elapsed_time += check_interval
                
                print(f"\n⏰ 等待超时 ({max_wait_time}s)，上链可能仍在进行中")
                return False
                
            else:
                print(f"❌ 支付处理失败: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ 测试过程中发生异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("🧪 开始测试真实自动上链流程...")
    success = test_auto_onchain()
    if success:
        print("\n🎉 测试成功！真实自动上链流程正常工作")
    else:
        print("\n❌ 测试失败或超时") 