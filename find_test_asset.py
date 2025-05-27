#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
查找可用于测试的资产
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.asset import Asset, AssetStatus
from app.models.admin import OnchainHistory
from app.extensions import db
import json

def find_test_assets():
    """查找可用于测试的资产"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔍 查找包含203906的资产...")
            
            # 查找包含203906的资产
            assets_203906 = Asset.query.filter(Asset.token_symbol.like('%203906%')).all()
            print(f"找到 {len(assets_203906)} 个包含203906的资产:")
            for asset in assets_203906:
                print(f"  - {asset.token_symbol} (ID: {asset.id}) - 状态: {asset.status} - 名称: {asset.name}")
                print(f"    Token地址: {asset.token_address}")
                print(f"    支付确认: {asset.payment_confirmed}")
            
            print(f"\n🔍 查找所有已上链的资产...")
            onchain_assets = Asset.query.filter_by(status=AssetStatus.ON_CHAIN.value).all()
            print(f"找到 {len(onchain_assets)} 个已上链的资产:")
            for asset in onchain_assets[:10]:  # 只显示前10个
                print(f"  - {asset.token_symbol} (ID: {asset.id}) - Token: {asset.token_address}")
                if asset.blockchain_details:
                    try:
                        details = json.loads(asset.blockchain_details)
                        if details.get('mock_mode'):
                            print(f"    ⚠️  模拟模式")
                    except:
                        pass
            
            print(f"\n🔍 查找支付确认但未上链的资产...")
            confirmed_assets = Asset.query.filter_by(
                status=AssetStatus.CONFIRMED.value,
                payment_confirmed=True
            ).filter(Asset.token_address.is_(None)).all()
            
            print(f"找到 {len(confirmed_assets)} 个支付确认但未上链的资产:")
            for asset in confirmed_assets[:5]:  # 只显示前5个
                print(f"  - {asset.token_symbol} (ID: {asset.id}) - 名称: {asset.name}")
                print(f"    支付确认时间: {asset.payment_confirmed_at}")
                print(f"    部署进行中: {asset.deployment_in_progress}")
            
            # 如果找到了包含203906的资产，选择第一个进行测试
            if assets_203906:
                test_asset = assets_203906[0]
                print(f"\n🎯 选择资产 {test_asset.token_symbol} 进行测试")
                return test_asset.token_symbol
            
            # 如果没有203906，选择一个已上链的资产进行重置测试
            elif onchain_assets:
                # 优先选择模拟模式的资产
                for asset in onchain_assets:
                    if asset.blockchain_details:
                        try:
                            details = json.loads(asset.blockchain_details)
                            if details.get('mock_mode'):
                                print(f"\n🎯 选择模拟模式资产 {asset.token_symbol} 进行测试")
                                return asset.token_symbol
                        except:
                            pass
                
                # 如果没有模拟模式的，选择第一个
                test_asset = onchain_assets[0]
                print(f"\n🎯 选择资产 {test_asset.token_symbol} 进行测试")
                return test_asset.token_symbol
            
            else:
                print("\n❌ 没有找到合适的测试资产")
                return None
                
        except Exception as e:
            print(f"❌ 查找资产失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

if __name__ == "__main__":
    print("🔍 查找可用于测试的资产...")
    test_symbol = find_test_assets()
    if test_symbol:
        print(f"\n✅ 建议使用资产: {test_symbol}")
    else:
        print("\n❌ 未找到合适的测试资产") 