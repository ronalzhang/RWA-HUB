#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
设置资产29状态为5（支付已确认），准备测试真实上链
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import Asset, AssetStatus

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def set_asset_29_status():
    """设置资产29状态为5（支付已确认）"""
    try:
        # 查找资产29
        asset = Asset.query.filter_by(id=29).first()
        
        if not asset:
            logger.error("未找到资产ID=29")
            return False
        
        logger.info(f"找到资产29: {asset.name}")
        logger.info(f"当前状态: {asset.status}")
        
        # 设置状态为5（支付已确认）
        asset.status = 5
        asset.updated_at = datetime.utcnow()
        
        # 清空可能的虚假token地址
        if asset.token_address and (asset.token_address == 'N/A' or len(asset.token_address) < 32):
            logger.info(f"清空虚假token地址: {asset.token_address}")
            asset.token_address = None
        
        # 清空可能的虚假deployment_tx_hash
        if asset.deployment_tx_hash and (asset.deployment_tx_hash == 'N/A' or len(asset.deployment_tx_hash) < 32):
            logger.info(f"清空虚假deployment_tx_hash: {asset.deployment_tx_hash}")
            asset.deployment_tx_hash = None
        
        # 重置部署标记
        asset.deployment_in_progress = False
        
        db.session.commit()
        
        logger.info(f"✅ 资产29状态已设置为5（支付已确认）")
        logger.info(f"资产名称: {asset.name}")
        logger.info(f"状态: {asset.status}")
        logger.info(f"Token地址: {asset.token_address}")
        logger.info(f"部署交易哈希: {asset.deployment_tx_hash}")
        logger.info(f"部署进行中: {asset.deployment_in_progress}")
        
        return True
        
    except Exception as e:
        logger.error(f"设置资产29状态失败: {str(e)}")
        db.session.rollback()
        return False

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