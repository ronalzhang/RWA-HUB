#!/usr/bin/env python3
"""
SOL余额充值和SPL Token创建解决方案
"""
import os
import sys
import time
from decimal import Decimal

# 将项目目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Asset
from app.services.spl_token_service import SplTokenService
from app.extensions import db

def create_minimal_spl_token():
    """创建单个SPL Token用于测试（如果有足够余额）"""
    app = create_app()

    with app.app_context():
        try:
            print("🧪 开始测试创建单个SPL Token...")

            # 检查余额
            platform_keypair = SplTokenService._get_platform_keypair()
            if not platform_keypair:
                print("❌ 无法获取平台私钥")
                return False

            from app.blockchain.solana_service import get_solana_client
            client = get_solana_client()
            balance_response = client.get_balance(platform_keypair.pubkey())
            balance_lamports = balance_response.value
            balance_sol = Decimal(balance_lamports) / Decimal(10**9)

            print(f"💰 当前SOL余额: {balance_sol:.9f} SOL")

            if balance_sol < Decimal("1.5"):
                print("❌ SOL余额不足，无法创建测试Token")
                return False

            # 找到第一个需要创建SPL Token的资产
            asset = Asset.query.filter(
                Asset.status == 2,  # AssetStatus.APPROVED
                Asset.spl_mint_address.is_(None)
            ).first()

            if not asset:
                print("✅ 所有资产都已有SPL Token")
                return True

            print(f"🎯 选择资产进行测试: {asset.token_symbol} (ID: {asset.id})")

            # 创建SPL Token
            result = SplTokenService.create_asset_token(asset.id)

            if result.get('success'):
                print(f"✅ 测试成功！SPL Token已创建")
                print(f"   Mint地址: {result.get('data', {}).get('mint_address')}")
                print(f"   交易哈希: {result.get('data', {}).get('tx_hash')}")
                return True
            else:
                print(f"❌ 测试失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 测试过程出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def show_funding_instructions():
    """显示充值说明"""
    print("\n" + "="*60)
    print("💡 SOL充值解决方案")
    print("="*60)

    platform_keypair = SplTokenService._get_platform_keypair()
    if platform_keypair:
        platform_address = str(platform_keypair.pubkey())
        print(f"\n📍 平台钱包地址: {platform_address}")
        print(f"\n💰 充值要求:")
        print(f"   - 每个SPL Token需要约 1.5616 SOL")
        print(f"   - 当前有9个资产需要创建Token")
        print(f"   - 建议充值: 15-20 SOL（包含缓冲）")

        print(f"\n🚀 充值方式:")
        print(f"   1. 使用Phantom钱包转账SOL到上述地址")
        print(f"   2. 使用交易所直接转账SOL")
        print(f"   3. 使用Solana命令行工具")

        print(f"\n⚡ 充值完成后运行:")
        print(f"   python create_spl_tokens.py")

        print(f"\n🔍 实时查看钱包余额:")
        print(f"   https://solscan.io/account/{platform_address}")

    print("\n" + "="*60)

def main():
    """主函数"""
    print("🚀 SPL Token创建解决方案")
    print("="*50)

    app = create_app()
    with app.app_context():
        # 检查余额
        from app.blockchain.solana_service import get_solana_client

        platform_keypair = SplTokenService._get_platform_keypair()
        if not platform_keypair:
            print("❌ 无法获取平台私钥")
            return

        client = get_solana_client()
        balance_response = client.get_balance(platform_keypair.pubkey())
        balance_lamports = balance_response.value
        balance_sol = Decimal(balance_lamports) / Decimal(10**9)

        platform_address = str(platform_keypair.pubkey())
        print(f"📍 平台钱包: {platform_address}")
        print(f"💰 当前余额: {balance_sol:.9f} SOL")

        # 检查需要创建的资产数量
        assets_count = Asset.query.filter(
            Asset.status == 2,
            Asset.spl_mint_address.is_(None)
        ).count()

        print(f"📦 待创建Token的资产: {assets_count} 个")

        required_sol = Decimal(str(assets_count)) * Decimal("1.5616")
        print(f"💸 所需SOL: ~{required_sol:.2f} SOL")

        if balance_sol >= Decimal("1.5616"):
            print(f"\n✅ 有足够余额创建至少1个Token，开始测试...")
            success = create_minimal_spl_token()
            if success:
                print(f"\n🎉 测试成功！继续创建剩余Token...")
                # 继续创建剩余的Token
                from create_spl_tokens import create_spl_tokens_for_existing_assets
                create_spl_tokens_for_existing_assets()
            else:
                print(f"\n❌ 测试失败，请检查错误信息")
        else:
            print(f"\n⚠️ SOL余额不足，需要先充值")
            show_funding_instructions()

if __name__ == "__main__":
    main()