#!/usr/bin/env python3
"""
手动触发资产29的上链操作
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Asset
from app.extensions import db
from app.services.asset_service import AssetService
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def trigger_asset_29_onchain():
    """手动触发资产29的上链操作"""
    app = create_app()
    
    with app.app_context():
        try:
            # 查询资产29
            asset = Asset.query.filter_by(id=29).first()
            if not asset:
                logger.error("❌ 资产29不存在")
                return
            
            logger.info(f"🚀 开始手动触发资产29上链操作...")
            logger.info(f"   资产名称: {asset.name}")
            logger.info(f"   当前状态: {asset.status}")
            
            # 确保资产状态为5（支付已确认）
            if asset.status != 5:
                logger.info(f"⚠️ 资产状态不是5，当前为{asset.status}，先设置为5...")
                asset.status = 5
                db.session.commit()
                logger.info("✅ 资产状态已设置为5")
            
            # 手动调用上链处理函数
            logger.info("🔄 开始执行上链处理...")
            service = AssetService()
            result = service.deploy_asset_to_blockchain(asset.id)
            
            if result.get('success'):
                logger.info(f"✅ 上链处理完成！代币地址: {result.get('token_address')}")
            else:
                logger.warning(f"⚠️ 上链处理失败: {result.get('error')}")
                
            # 重新查询资产状态
            db.session.refresh(asset)
            logger.info(f"📊 处理后资产状态: {asset.status}")
            
            # 查询最新的上链历史
            from app.models import OnchainHistory
            latest_history = OnchainHistory.query.filter_by(asset_id=29).order_by(OnchainHistory.created_at.desc()).first()
            
            if latest_history:
                logger.info(f"📈 最新上链记录:")
                logger.info(f"   时间: {latest_history.created_at}")
                logger.info(f"   状态: {latest_history.status}")
                logger.info(f"   交易哈希: {latest_history.transaction_hash}")
                logger.info(f"   错误信息: {latest_history.error_message}")
                logger.info(f"   触发类型: {latest_history.trigger_type}")
            
        except Exception as e:
            logger.error(f"❌ 手动触发上链操作时出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    trigger_asset_29_onchain() 