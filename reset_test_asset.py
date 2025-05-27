#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
重置RH-101727资产状态脚本
用于测试真实自动上链流程
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.asset import Asset, AssetStatus
from app.models.admin import OnchainHistory
from app.extensions import db
from datetime import datetime
import json

def reset_test_asset(asset_symbol='RH-101727'):
    """重置测试资产状态"""
    app = create_app()
    
    with app.app_context():
        try:
            # 查找资产
            asset = Asset.query.filter_by(token_symbol=asset_symbol).first()
            
            if not asset:
                print(f"❌ 未找到{asset_symbol}资产")
                return False
            
            print(f"📋 找到资产: {asset.name} (ID: {asset.id})")
            print(f"当前状态: {asset.status}")
            print(f"Token地址: {asset.token_address}")
            print(f"部署交易哈希: {asset.deployment_tx_hash}")
            print(f"支付确认: {asset.payment_confirmed}")
            print(f"支付确认时间: {asset.payment_confirmed_at}")
            print(f"部署进行中: {asset.deployment_in_progress}")
            print(f"部署时间: {asset.deployment_time}")
            
            # 检查区块链详情
            if asset.blockchain_details:
                try:
                    details = json.loads(asset.blockchain_details)
                    print(f"区块链详情: {details}")
                    if details.get('mock_mode'):
                        print("⚠️  检测到模拟模式标记")
                except:
                    print(f"区块链详情(原始): {asset.blockchain_details}")
            
            # 检查上链历史记录
            history_records = OnchainHistory.query.filter_by(asset_id=asset.id).all()
            print(f"\n📊 上链历史记录 ({len(history_records)} 条):")
            for record in history_records:
                print(f"  - ID: {record.id}, 状态: {record.status}, 触发类型: {record.trigger_type}")
                print(f"    交易哈希: {record.transaction_hash}, 错误信息: {record.error_message}")
            
            print(f"\n🔄 准备重置资产状态以测试真实上链...")
            
            # 重置资产状态
            print("正在重置资产状态...")
            
            # 1. 清除上链相关字段
            asset.token_address = None
            asset.deployment_tx_hash = None
            asset.deployment_time = None
            asset.deployment_in_progress = False
            asset.deployment_started_at = None
            
            # 2. 设置为支付确认状态
            asset.status = AssetStatus.CONFIRMED.value
            asset.payment_confirmed = True
            asset.payment_confirmed_at = datetime.utcnow()
            
            # 3. 清除模拟模式标记
            if asset.blockchain_details:
                try:
                    details = json.loads(asset.blockchain_details)
                    if 'mock_mode' in details:
                        del details['mock_mode']
                    if 'deployment_time' in details:
                        del details['deployment_time']
                    asset.blockchain_details = json.dumps(details) if details else None
                except:
                    asset.blockchain_details = None
            
            # 4. 确保支付详情正确
            payment_info = {
                'status': 'confirmed',
                'confirmed_at': datetime.utcnow().isoformat(),
                'amount': 100.0,
                'tx_hash': f'test_payment_hash_for_{asset_symbol}',
                'wallet_address': 'test_wallet_for_auto_onchain'
            }
            asset.payment_details = json.dumps(payment_info)
            
            # 5. 清除现有的上链历史记录（重新开始）
            for record in history_records:
                db.session.delete(record)
            
            db.session.commit()
            
            print("✅ 资产状态重置完成!")
            print(f"新状态: {asset.status} (CONFIRMED)")
            print(f"支付确认: {asset.payment_confirmed}")
            print(f"Token地址: {asset.token_address} (已清除)")
            print(f"部署进行中: {asset.deployment_in_progress}")
            
            print(f"\n🎯 资产 {asset.token_symbol} 现在处于支付确认状态，可以触发真实上链操作")
            
            return True
            
        except Exception as e:
            print(f"❌ 重置资产状态失败: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("🔍 重置测试资产状态...")
    success = reset_test_asset()
    if success:
        print("\n✅ 重置完成，可以开始测试真实自动上链流程")
    else:
        print("\n❌ 重置失败") 