#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
更新数据库中的SOL地址格式
将小写的SOL地址更新为正确的大小写格式
"""

from app import create_app, db
from app.models.trade import Trade
from app.models.asset import Asset
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 小写SOL地址
LOWERCASE_SOL_ADDRESS = 'eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr'
# 正确大小写的SOL地址
CORRECT_SOL_ADDRESS = 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR'

def update_sol_addresses():
    """更新数据库中的SOL地址格式"""
    app = create_app()
    with app.app_context():
        try:
            # 1. 更新交易记录中的地址
            logger.info("开始更新交易记录中的SOL地址...")
            trades = Trade.query.filter(Trade.trader_address.like(LOWERCASE_SOL_ADDRESS)).all()
            logger.info(f"找到 {len(trades)} 条需要更新的交易记录")
            
            for trade in trades:
                logger.info(f"更新交易记录 ID: {trade.id}, 原地址: {trade.trader_address}")
                trade.trader_address = CORRECT_SOL_ADDRESS
                db.session.add(trade)
            
            # 2. 更新资产记录中的地址
            logger.info("开始更新资产记录中的SOL地址...")
            assets = Asset.query.filter(Asset.owner_address.like(LOWERCASE_SOL_ADDRESS)).all()
            logger.info(f"找到 {len(assets)} 条需要更新的资产记录")
            
            for asset in assets:
                logger.info(f"更新资产记录 ID: {asset.id}, 原地址: {asset.owner_address}")
                asset.owner_address = CORRECT_SOL_ADDRESS
                db.session.add(asset)
                
            # 提交所有更改
            db.session.commit()
            logger.info("所有SOL地址更新完成")
            
            # 验证更新结果
            updated_trades = Trade.query.filter(Trade.trader_address == CORRECT_SOL_ADDRESS).all()
            logger.info(f"更新后的交易记录数量: {len(updated_trades)}")
            
            updated_assets = Asset.query.filter(Asset.owner_address == CORRECT_SOL_ADDRESS).all()
            logger.info(f"更新后的资产记录数量: {len(updated_assets)}")
            
        except Exception as e:
            logger.error(f"更新SOL地址时出错: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    update_sol_addresses() 