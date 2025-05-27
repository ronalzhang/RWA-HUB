#!/usr/bin/env python3
"""
修复资产创建问题的脚本
1. 修复 Total Value 显示问题
2. 修复状态更新问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import Asset, AssetStatus
from datetime import datetime
import json

def fix_asset_creation_issues():
    """修复资产创建相关问题"""
    app = create_app()
    
    with app.app_context():
        print("🔧 开始修复资产创建问题...")
        
        # 1. 检查最近创建的资产
        recent_assets = Asset.query.filter(
            Asset.created_at >= datetime(2025, 5, 27)  # 今天创建的资产
        ).order_by(Asset.created_at.desc()).all()
        
        print(f"📋 找到 {len(recent_assets)} 个最近创建的资产")
        
        for asset in recent_assets:
            print(f"\n🔍 检查资产: ID={asset.id}, 名称={asset.name}")
            print(f"   状态: {asset.status}")
            print(f"   Total Value: {asset.total_value}")
            print(f"   支付确认: {asset.payment_confirmed}")
            print(f"   支付哈希: {asset.payment_tx_hash}")
            
            # 检查是否需要修复 total_value
            if asset.total_value is None or asset.total_value == 0:
                print(f"   ⚠️  Total Value 为空或0，需要修复")
                
                # 尝试从 token_supply 和 token_price 计算
                if asset.token_supply and asset.token_price:
                    calculated_value = asset.token_supply * asset.token_price
                    asset.total_value = calculated_value
                    print(f"   ✅ 修复 Total Value: {calculated_value}")
                else:
                    print(f"   ❌ 无法计算 Total Value，缺少必要数据")
            
            # 检查支付状态
            if asset.payment_tx_hash and not asset.payment_confirmed and asset.status == AssetStatus.PENDING.value:
                print(f"   ⚠️  有支付哈希但未确认，状态为 PENDING")
                
                # 手动触发支付确认检查
                try:
                    from app.tasks import monitor_creation_payment_task
                    print(f"   🔄 重新触发支付确认监控...")
                    monitor_creation_payment_task.delay(asset.id, asset.payment_tx_hash)
                    print(f"   ✅ 支付确认监控任务已触发")
                except Exception as e:
                    print(f"   ❌ 触发支付确认监控失败: {e}")
        
        # 提交数据库更改
        try:
            db.session.commit()
            print(f"\n✅ 数据库更改已提交")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ 数据库提交失败: {e}")
            return False
        
        return True

def check_asset_creation_api():
    """检查资产创建API的实现"""
    print("\n🔍 检查资产创建API实现...")
    
    # 检查 assets.py 中的创建API
    try:
        with open('app/routes/assets.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查是否正确处理 total_value
        if 'total_value=data.get(\'total_value\')' in content:
            print("✅ API 正确处理 total_value 字段")
        else:
            print("❌ API 未正确处理 total_value 字段")
            
        # 检查是否触发支付监控
        if 'monitor_creation_payment_task.delay' in content:
            print("✅ API 正确触发支付监控任务")
        else:
            print("❌ API 未触发支付监控任务")
            
    except Exception as e:
        print(f"❌ 检查API文件失败: {e}")

def test_payment_monitoring():
    """测试支付监控功能"""
    print("\n🧪 测试支付监控功能...")
    
    app = create_app()
    with app.app_context():
        # 查找有支付哈希但未确认的资产
        pending_assets = Asset.query.filter(
            Asset.payment_tx_hash.isnot(None),
            Asset.payment_confirmed == False,
            Asset.status == AssetStatus.PENDING.value
        ).all()
        
        print(f"📋 找到 {len(pending_assets)} 个待确认支付的资产")
        
        for asset in pending_assets:
            print(f"🔄 测试资产 {asset.id} 的支付监控...")
            
            try:
                from app.tasks import monitor_creation_payment
                # 直接调用监控函数（不使用异步）
                monitor_creation_payment(asset.id, asset.payment_tx_hash, max_retries=3, retry_interval=5)
                print(f"✅ 资产 {asset.id} 支付监控完成")
            except Exception as e:
                print(f"❌ 资产 {asset.id} 支付监控失败: {e}")

if __name__ == "__main__":
    print("🚀 开始修复资产创建问题...")
    
    # 1. 修复现有资产问题
    if fix_asset_creation_issues():
        print("✅ 资产问题修复完成")
    else:
        print("❌ 资产问题修复失败")
    
    # 2. 检查API实现
    check_asset_creation_api()
    
    # 3. 测试支付监控
    test_payment_monitoring()
    
    print("\n🎉 修复脚本执行完成！") 