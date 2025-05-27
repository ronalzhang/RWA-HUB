#!/usr/bin/env python3
"""
将资产29的状态设置为2
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Asset
from app.extensions import db
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def set_asset_29_status_2():
    """将资产29的状态设置为2"""
    app = create_app()
    
    with app.app_context():
        try:
            # 查询资产29
            asset = Asset.query.filter_by(id=29).first()
            if not asset:
                logger.error("❌ 资产29不存在")
                return
            
            logger.info(f"📊 资产29当前状态: {asset.status}")
            
            # 设置状态为2
            asset.status = 2
            db.session.commit()
            
            logger.info(f"✅ 资产29状态已设置为2")
            
            # 验证设置
            asset = Asset.query.filter_by(id=29).first()
            logger.info(f"🔍 验证：资产29当前状态为 {asset.status}")
            
        except Exception as e:
            logger.error(f"❌ 设置状态时出错: {e}")
            db.session.rollback()

if __name__ == "__main__":
    set_asset_29_status_2() 