#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
将资产29的状态设置为5以触发自动上链
"""

import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.asset import Asset, AssetStatus

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def set_asset_29_status():
    app = create_app()
    
    with app.app_context():
        print("=== 设置资产29状态为5（支付已确认）===\n")
        
        # 获取资产29
        asset_29 = Asset.query.get(29)
        if not asset_29:
            print("❌ 资产29不存在")
            return
        
        print(f"📋 资产29当前状态:")
        print(f"   ID: {asset_29.id}")
        print(f"   名称: {asset_29.name}")
        print(f"   当前状态: {asset_29.status}")
        print(f"   Token地址: {asset_29.token_address}")
        print(f"   支付确认: {asset_29.payment_confirmed}")
        print(f"   部署进行中: {asset_29.deployment_in_progress}")
        print()
        
        # 检查是否满足修改条件
        if asset_29.token_address:
            print("⚠️  警告：资产已有Token地址，可能已经上链")
            print("   建议先清理Token地址再设置状态")
            return
        
        if asset_29.deployment_in_progress:
            print("⚠️  警告：资产正在部署中")
            return
        
        # 设置状态为5（支付已确认）
        print("🔄 设置资产状态为5（支付已确认）...")
        asset_29.status = AssetStatus.CONFIRMED.value  # 5
        asset_29.payment_confirmed = True
        asset_29.deployment_in_progress = False
        asset_29.error_message = None
        asset_29.updated_at = datetime.utcnow()
        
        # 提交更改
        db.session.commit()
        
        print("✅ 资产29状态已设置为5")
        print()
        
        # 验证修改结果
        print("🔍 验证修改结果:")
        asset_29_after = Asset.query.get(29)
        print(f"   状态: {asset_29_after.status} (应该是5)")
        print(f"   支付确认: {asset_29_after.payment_confirmed} (应该是True)")
        print(f"   Token地址: {asset_29_after.token_address} (应该是None)")
        print(f"   部署进行中: {asset_29_after.deployment_in_progress} (应该是False)")
        print()
        
        # 检查自动上链条件
        should_auto_onchain = (
            asset_29_after.status == AssetStatus.CONFIRMED.value and
            asset_29_after.payment_confirmed and
            not asset_29_after.token_address and
            not asset_29_after.deployment_in_progress
        )
        
        if should_auto_onchain:
            print("🎉 资产29现在满足自动上链条件！")
            print("🔄 自动上链任务将在下次执行时处理（每5分钟）")
            print("📊 您可以在后台管理的上链历史标签页查看进度")
        else:
            print("❌ 资产29仍不满足自动上链条件")
            if asset_29_after.status != AssetStatus.CONFIRMED.value:
                print(f"   - 状态不正确: {asset_29_after.status} (应该是5)")
            if not asset_29_after.payment_confirmed:
                print("   - 支付未确认")
            if asset_29_after.token_address:
                print("   - 已有Token地址")
            if asset_29_after.deployment_in_progress:
                print("   - 部署进行中")
        
        print("\n=== 操作完成 ===")

def check_auto_onchain_conditions():
    """检查自动上链条件"""
    try:
        logger.info("=" * 50)
        logger.info("检查自动上链条件")
        logger.info("=" * 50)
        
        # 检查环境配置
        solana_url = os.environ.get("SOLANA_NETWORK_URL")
        logger.info(f"Solana网络URL: {solana_url}")
        
        private_key = os.environ.get("SOLANA_PRIVATE_KEY_ENCRYPTED") or os.environ.get("SOLANA_PRIVATE_KEY")
        if private_key:
            logger.info("✅ 找到Solana私钥配置")
        else:
            logger.error("❌ 未找到Solana私钥配置")
        
        # 检查solana-py库
        try:
            import solana
            logger.info(f"✅ solana-py库已安装，版本: {solana.__version__}")
        except ImportError:
            logger.error("❌ solana-py库未安装")
        
        # 检查自动上链任务
        from app.tasks import check_pending_assets_for_onchain
        logger.info("✅ 自动上链任务函数可用")
        
        # 检查资产状态
        pending_assets = Asset.query.filter(
            Asset.status == 5,  # 支付已确认
            Asset.deleted_at.is_(None),
            Asset.deployment_in_progress == False
        ).all()
        
        logger.info(f"符合上链条件的资产数量: {len(pending_assets)}")
        for asset in pending_assets:
            logger.info(f"  - 资产ID={asset.id}, 名称={asset.name}")
        
        return True
        
    except Exception as e:
        logger.error(f"检查自动上链条件失败: {str(e)}")
        return False

def main():
    """主函数"""
    logger.info("开始设置资产29状态并检查上链条件...")
    
    # 创建Flask应用上下文
    app = create_app()
    
    with app.app_context():
        try:
            # 1. 设置资产29状态
            if set_asset_29_status():
                logger.info("✅ 资产29状态设置成功")
            else:
                logger.error("❌ 资产29状态设置失败")
                return
            
            # 2. 检查自动上链条件
            if check_auto_onchain_conditions():
                logger.info("✅ 自动上链条件检查完成")
            else:
                logger.error("❌ 自动上链条件检查失败")
                return
            
            logger.info("=" * 60)
            logger.info("🎯 资产29已准备好进行真实上链测试！")
            logger.info("=" * 60)
            logger.info("接下来系统将在5分钟内自动尝试上链...")
            logger.info("请监控PM2日志查看上链进度:")
            logger.info("  pm2 logs rwa-hub")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"执行过程中发生错误: {str(e)}")
            raise

if __name__ == "__main__":
    main() 