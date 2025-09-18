#!/usr/bin/env python3
"""
检查并发现现有资产的SPL Token
"""
import os
import sys

# 将项目目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Asset
from app.blockchain.solana_service import get_solana_client
from app.extensions import db
from solders.pubkey import Pubkey

def search_tokens_by_symbol():
    """通过资产符号搜索可能的SPL Token"""
    app = create_app()

    with app.app_context():
        try:
            print("🔍 搜索现有资产的SPL Token...")
            print("="*50)

            # 获取所有没有SPL Token记录的资产
            assets_without_spl = Asset.query.filter(
                Asset.status == 2,
                Asset.spl_mint_address.is_(None)
            ).all()

            client = get_solana_client()

            print(f"检查 {len(assets_without_spl)} 个资产的Token状态:\n")

            found_tokens = []

            for asset in assets_without_spl:
                print(f"📦 {asset.token_symbol} - {asset.name}")
                print(f"   创建者: {asset.creator_address}")
                print(f"   供应量: {asset.token_supply:,}")

                # 这里我们需要想办法找到对应的Token
                # 可能的方法：
                # 1. 通过创建者地址查找他们创建的所有Token
                # 2. 通过Token符号匹配
                # 3. 通过供应量匹配

                # 先记录基本信息，需要更多信息来查找
                found_tokens.append({
                    'symbol': asset.token_symbol,
                    'creator': asset.creator_address,
                    'supply': asset.token_supply,
                    'asset_id': asset.id
                })
                print()

            print("💡 查找建议:")
            print("1. 检查Solscan上创建者地址的Token历史")
            print("2. 根据Token符号和供应量匹配")
            print("3. 手动提供已知的Token地址进行关联")

            return found_tokens

        except Exception as e:
            print(f"❌ 搜索过程出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

def link_known_token(asset_symbol, token_address):
    """手动关联已知的Token地址到资产"""
    app = create_app()

    with app.app_context():
        try:
            asset = Asset.query.filter_by(token_symbol=asset_symbol).first()
            if not asset:
                print(f"❌ 未找到资产 {asset_symbol}")
                return False

            # 验证Token地址是否有效
            client = get_solana_client()
            try:
                token_info = client.get_token_supply(Pubkey.from_string(token_address))
                if token_info.value:
                    actual_supply = int(token_info.value.amount) / (10 ** token_info.value.decimals)

                    print(f"✅ Token验证成功:")
                    print(f"   资产: {asset_symbol}")
                    print(f"   Token地址: {token_address}")
                    print(f"   链上供应量: {actual_supply:,.0f}")
                    print(f"   数据库供应量: {asset.token_supply:,}")

                    # 检查供应量是否匹配
                    if int(actual_supply) == asset.token_supply:
                        print(f"   ✅ 供应量匹配")

                        # 关联到数据库
                        asset.spl_mint_address = token_address
                        asset.spl_creation_status = 2  # COMPLETED
                        asset.spl_creation_tx_hash = 'existing_token'
                        db.session.commit()

                        print(f"   ✅ 已关联到数据库")
                        return True
                    else:
                        print(f"   ⚠️ 供应量不匹配，请确认")
                        return False
                else:
                    print(f"❌ Token地址无效: {token_address}")
                    return False

            except Exception as e:
                print(f"❌ Token验证失败: {e}")
                return False

        except Exception as e:
            print(f"❌ 关联过程出错: {str(e)}")
            return False

if __name__ == "__main__":
    print("🚀 开始搜索现有资产的SPL Token...")
    found_tokens = search_tokens_by_symbol()

    print(f"\n📋 发现的资产列表:")
    for token in found_tokens:
        print(f"- {token['symbol']}: 创建者 {token['creator']}, 供应量 {token['supply']:,}")

    print(f"\n💡 要关联已知Token，请使用:")
    print(f"python find_existing_tokens.py")
    print(f"然后调用 link_known_token('资产符号', 'Token地址')")