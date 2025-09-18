#!/usr/bin/env python3
"""
检查并修复SPL Token配置问题
"""
import os
import sys

# 将项目目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Asset
from app.models.admin import SystemConfig
from app.extensions import db

def check_spl_configuration():
    """检查SPL Token配置状态"""
    app = create_app()

    with app.app_context():
        try:
            print("🔍 SPL Token配置检查报告")
            print("="*50)

            # 1. 检查地址配置
            print("\n📍 地址配置检查:")
            platform_addresses = [
                'PLATFORM_FEE_ADDRESS',
                'ASSET_CREATION_FEE_ADDRESS',
                'PLATFORM_WALLET_ADDRESS',
                'SOLANA_WALLET_ADDRESS'
            ]

            main_address = 'H6FMXx3s1kq1aMkYHiexVzircV31WnWaP5MSQQwfHfeW'

            for addr_key in platform_addresses:
                config_value = SystemConfig.get_value(addr_key)
                match_status = "✅" if config_value == main_address else "❌"
                print(f"   {addr_key}: {config_value} {match_status}")

            # 2. 检查私钥配置
            print("\n🔐 私钥配置检查:")
            from app.services.spl_token_service import SplTokenService
            platform_keypair = SplTokenService._get_platform_keypair()
            if platform_keypair:
                current_address = str(platform_keypair.pubkey())
                match_status = "✅" if current_address == main_address else "❌"
                print(f"   PLATFORM_SPL_KEYPAIR对应地址: {current_address} {match_status}")

                if current_address != main_address:
                    print(f"   ⚠️ 配置不匹配！期望地址: {main_address}")
            else:
                print("   ❌ 无法获取平台私钥")

            # 3. 检查已有SPL Token状态
            print("\n🪙 SPL Token状态:")
            assets_with_spl = Asset.query.filter(Asset.spl_mint_address.isnot(None)).all()
            assets_without_spl = Asset.query.filter(
                Asset.status == 2,
                Asset.spl_mint_address.is_(None)
            ).all()

            print(f"   已有SPL Token的资产: {len(assets_with_spl)} 个")
            for asset in assets_with_spl:
                print(f"     - {asset.token_symbol}: {asset.spl_mint_address}")

            print(f"   需要创建SPL Token的资产: {len(assets_without_spl)} 个")
            for asset in assets_without_spl:
                print(f"     - {asset.token_symbol} (ID: {asset.id})")

            # 4. 给出建议
            print("\n💡 建议操作:")
            if current_address != main_address:
                print("   1. 需要更新PLATFORM_SPL_KEYPAIR配置使用正确的私钥")
                print(f"   2. 或者给地址 {current_address} 充值SOL")

            if len(assets_without_spl) > 0:
                print("   3. 为剩余8个资产创建SPL Token")

            print("   4. 测试购买流程确保mint功能正常")

            return {
                'address_match': current_address == main_address,
                'assets_with_spl': len(assets_with_spl),
                'assets_without_spl': len(assets_without_spl),
                'current_keypair_address': current_address,
                'expected_address': main_address
            }

        except Exception as e:
            print(f"❌ 检查过程出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

def suggest_next_steps(check_result):
    """根据检查结果提供下一步建议"""
    if not check_result:
        return

    print("\n🚀 下一步操作建议:")
    print("="*50)

    if not check_result['address_match']:
        print("🔧 方案1: 更新私钥配置（推荐）")
        print("   - 使用主地址H6FMXx3s1kq1aMkYHiexVzircV31WnWaP5MSQQwfHfeW的私钥")
        print("   - 更新PLATFORM_SPL_KEYPAIR配置")
        print(f"   - 主地址有 {check_result.get('main_address_balance', 'unknown')} SOL")

        print("\n🔧 方案2: 给当前地址充值")
        print(f"   - 给 {check_result['current_keypair_address']} 充值SOL")
        print("   - 需要约12-15 SOL来创建剩余Token")

    if check_result['assets_without_spl'] > 0:
        print(f"\n📦 创建剩余{check_result['assets_without_spl']}个SPL Token:")
        print("   python create_spl_tokens.py")

    print("\n✅ 测试购买流程:")
    print("   - 访问资产页面进行小额测试购买")
    print("   - 验证用户收到真正的SPL Token")

if __name__ == "__main__":
    print("🚀 开始SPL Token配置检查...")
    result = check_spl_configuration()
    suggest_next_steps(result)