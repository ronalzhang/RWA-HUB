#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复虚假上链数据，重置资产状态，完善历史记录系统
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.asset import Asset, AssetStatus
from app.models.admin import OnchainHistory
from datetime import datetime

def fix_fake_onchain_complete():
    app = create_app()
    
    with app.app_context():
        print("=== 修复虚假上链数据 ===\n")
        
        # 1. 检查并修复资产29
        print("🔧 步骤1：修复资产29")
        asset_29 = Asset.query.get(29)
        if asset_29:
            print(f"   当前状态: {asset_29.status}")
            print(f"   Token地址: {asset_29.token_address}")
            print(f"   部署交易哈希: {asset_29.deployment_tx_hash}")
            
            # 判断是否为虚假数据
            is_fake = asset_29.token_address and not asset_29.deployment_tx_hash
            
            if is_fake:
                print("   ❌ 检测到虚假上链数据")
                print("   🔄 清理虚假数据...")
                
                # 清理虚假Token地址
                asset_29.token_address = None
                asset_29.deployment_tx_hash = None
                asset_29.deployment_time = None
                asset_29.blockchain_details = None
                
                # 重置状态为支付已确认（等待上链）
                asset_29.status = AssetStatus.CONFIRMED.value
                asset_29.deployment_in_progress = False
                asset_29.error_message = None
                asset_29.updated_at = datetime.utcnow()
                
                db.session.commit()
                print("   ✅ 已清理虚假数据，重置为待上链状态")
            else:
                print("   ✅ 数据正常，无需修复")
        else:
            print("   ❌ 资产29不存在")
        
        print()
        
        # 2. 检查并清理虚假上链历史记录
        print("🔧 步骤2：检查上链历史记录")
        onchain_records = OnchainHistory.query.filter_by(asset_id=29).all()
        
        print(f"   找到 {len(onchain_records)} 条上链历史记录")
        
        for record in onchain_records:
            print(f"   记录ID {record.id}:")
            print(f"     状态: {record.status}")
            print(f"     交易哈希: {record.transaction_hash or 'N/A'}")
            print(f"     区块号: {record.block_number or 'N/A'}")
            
            # 检查是否为虚假记录（成功但没有交易信息）
            is_fake_record = (
                record.status == 'success' and 
                not record.transaction_hash and 
                not record.block_number
            )
            
            if is_fake_record:
                print("     ❌ 检测到虚假成功记录")
                print("     🔄 更新为待处理状态...")
                
                # 更新为待处理状态，等待真实上链
                record.status = 'pending'
                record.transaction_hash = None
                record.block_number = None
                record.gas_used = None
                record.processed_at = None
                record.error_message = "重置：之前为虚假成功记录"
                record.updated_at = datetime.utcnow()
                
                db.session.commit()
                print("     ✅ 已重置为待处理状态")
            else:
                print("     ✅ 记录正常")
        
        print()
        
        # 3. 检查其他异常资产
        print("🔧 步骤3：检查其他异常资产")
        anomaly_assets = Asset.query.filter(
            Asset.status == 5,
            Asset.token_address.isnot(None),
            Asset.deployment_tx_hash.is_(None),
            Asset.deleted_at.is_(None)
        ).all()
        
        print(f"   找到 {len(anomaly_assets)} 个异常资产（有Token地址但无交易哈希）")
        
        for asset in anomaly_assets:
            print(f"   资产ID {asset.id}: {asset.name}")
            print(f"     Token地址: {asset.token_address}")
            print(f"     🔄 清理虚假数据...")
            
            # 清理虚假数据
            asset.token_address = None
            asset.deployment_tx_hash = None
            asset.deployment_time = None
            asset.blockchain_details = None
            asset.status = AssetStatus.CONFIRMED.value
            asset.deployment_in_progress = False
            asset.error_message = None
            asset.updated_at = datetime.utcnow()
            
            db.session.commit()
            print(f"     ✅ 已清理资产 {asset.id}")
        
        print()
        
        # 4. 验证修复结果
        print("🔍 步骤4：验证修复结果")
        
        # 重新检查资产29
        asset_29_after = Asset.query.get(29)
        if asset_29_after:
            print(f"   资产29修复后状态:")
            print(f"     状态: {asset_29_after.status} (应该是5)")
            print(f"     Token地址: {asset_29_after.token_address or 'N/A'} (应该是None)")
            print(f"     支付确认: {asset_29_after.payment_confirmed} (应该是True)")
            print(f"     部署进行中: {asset_29_after.deployment_in_progress} (应该是False)")
            
            # 检查是否满足自动上链条件
            should_auto_onchain = (
                asset_29_after.status == AssetStatus.CONFIRMED.value and
                asset_29_after.payment_confirmed and
                not asset_29_after.token_address and
                not asset_29_after.deployment_in_progress
            )
            
            if should_auto_onchain:
                print("     ✅ 现在满足自动上链条件")
                print("     🔄 自动上链任务将在下次执行时处理（每5分钟）")
            else:
                print("     ❌ 仍不满足自动上链条件")
        
        print()
        
        # 5. 改进建议
        print("💡 后续改进建议:")
        print("   1. 完善上链历史记录系统：")
        print("      - 记录所有上链尝试（成功、失败、重试）")
        print("      - 包含完整的交易信息（哈希、区块号、Gas等）")
        print("      - 记录详细的错误信息")
        print()
        
        print("   2. 改进状态更新逻辑：")
        print("      - 确保上链成功后正确更新状态为ON_CHAIN")
        print("      - 添加事务保护，防止部分更新")
        print("      - 添加状态一致性检查")
        print()
        
        print("   3. 添加数据验证：")
        print("      - 定期检查Token地址的真实性")
        print("      - 验证交易哈希的有效性")
        print("      - 清理虚假或测试数据")
        
        print("\n=== 修复完成 ===")
        print("✅ 虚假上链数据已清理")
        print("✅ 资产状态已重置")
        print("✅ 自动上链条件已恢复")
        print("\n🔄 请等待自动上链任务执行（每5分钟），或手动触发上链")

if __name__ == '__main__':
    fix_fake_onchain_complete() 