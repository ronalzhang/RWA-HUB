#!/usr/bin/env python3
"""
批量为现有资产创建SPL Token的脚本
"""
import os
import sys
import time
from flask import Flask

# 将项目目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Asset
from app.services.spl_token_service import SplTokenService
from app.extensions import db

def create_spl_tokens_for_existing_assets():
    """为现有的已批准资产创建SPL Token"""
    app = create_app()

    with app.app_context():
        try:
            # 获取所有已批准但没有SPL Token的资产
            assets_without_spl = Asset.query.filter(
                Asset.status == 2,  # AssetStatus.APPROVED
                Asset.spl_mint_address.is_(None)
            ).all()

            print(f"🔍 找到 {len(assets_without_spl)} 个需要创建SPL Token的资产")

            if not assets_without_spl:
                print("✅ 所有已批准的资产都已有SPL Token")
                return

            success_count = 0
            failed_count = 0

            for i, asset in enumerate(assets_without_spl, 1):
                print(f"\n📦 [{i}/{len(assets_without_spl)}] 为资产 {asset.token_symbol} (ID: {asset.id}) 创建SPL Token...")

                try:
                    # 调用SPL Token创建服务
                    result = SplTokenService.create_asset_token(asset.id)

                    if result.get('success'):
                        print(f"✅ 成功创建SPL Token: {result.get('mint_address')}")
                        success_count += 1

                        # 等待一下，避免RPC限制
                        time.sleep(2)
                    else:
                        print(f"❌ 创建失败: {result.get('message', '未知错误')}")
                        failed_count += 1

                except Exception as e:
                    print(f"❌ 创建失败: {str(e)}")
                    failed_count += 1

                # 每5个资产后稍作休息
                if i % 5 == 0:
                    print(f"⏸️ 处理了 {i} 个资产，休息 5 秒...")
                    time.sleep(5)

            print(f"\n🎯 批量创建完成:")
            print(f"   ✅ 成功: {success_count}")
            print(f"   ❌ 失败: {failed_count}")
            print(f"   📊 总计: {len(assets_without_spl)}")

        except Exception as e:
            print(f"❌ 批量创建过程中出错: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🚀 开始为现有资产批量创建SPL Token...")
    create_spl_tokens_for_existing_assets()
    print("🏁 脚本执行完成")