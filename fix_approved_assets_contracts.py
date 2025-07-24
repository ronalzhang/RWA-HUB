#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复已通过资产的合约地址脚本
专门为状态为2（已通过）但没有合约地址的资产添加合约地址
"""

import os
import sys
import json
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置Flask应用上下文
from app import create_app, db
from app.models.asset import Asset
from sqlalchemy import or_

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_contracts.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def fix_approved_assets_contracts():
    """修复已通过资产的合约地址"""
    app = create_app('production')  # 使用生产环境配置
    
    with app.app_context():
        try:
            logger.info("开始修复已通过资产的合约地址...")
            
            # 查询状态为2（已通过）但没有token_address的资产
            assets_to_fix = Asset.query.filter(
                Asset.status == 2,  # 只处理已通过的资产
                or_(Asset.token_address.is_(None), Asset.token_address == '')
            ).all()
            
            logger.info(f"找到 {len(assets_to_fix)} 个需要修复合约地址的已通过资产")
            
            if not assets_to_fix:
                logger.info("没有需要修复的资产")
                return
            
            # 显示需要修复的资产信息
            logger.info("需要修复的资产列表:")
            for asset in assets_to_fix:
                logger.info(f"  ID: {asset.id}, 名称: {asset.name}, 符号: {asset.token_symbol}")
            
            # 导入区块链服务
            from app.blockchain.rwa_contract_service import rwa_contract_service
            
            fixed_count = 0
            failed_assets = []
            
            for asset in assets_to_fix:
                try:
                    logger.info(f"处理资产: ID={asset.id}, 名称={asset.name}, 符号={asset.token_symbol}")
                    
                    # 生成合约地址
                    contract_result = rwa_contract_service.create_asset_directly(
                        creator_address=asset.creator_address,
                        asset_name=asset.name,
                        asset_symbol=asset.token_symbol,
                        total_supply=asset.token_supply,
                        decimals=0,
                        price_per_token=asset.token_price
                    )
                    
                    if contract_result['success']:
                        # 更新资产信息
                        asset.token_address = contract_result['mint_account']
                        asset.blockchain_data = json.dumps(contract_result['blockchain_data'])
                        asset.updated_at = datetime.now()
                        
                        fixed_count += 1
                        logger.info(f"✅ 资产 {asset.id} 合约地址修复成功")
                        logger.info(f"   代币地址: {asset.token_address}")
                    else:
                        error_msg = contract_result.get('error', '未知错误')
                        failed_assets.append({
                            'id': asset.id,
                            'name': asset.name,
                            'error': error_msg
                        })
                        logger.error(f"❌ 资产 {asset.id} 合约地址生成失败: {error_msg}")
                        
                except Exception as e:
                    failed_assets.append({
                        'id': asset.id,
                        'name': asset.name,
                        'error': str(e)
                    })
                    logger.error(f"❌ 修复资产 {asset.id} 时发生异常: {str(e)}")
            
            # 提交所有更改
            if fixed_count > 0:
                db.session.commit()
                logger.info(f"✅ 成功修复了 {fixed_count} 个资产的合约地址")
            else:
                logger.info("没有成功修复任何资产")
            
            # 显示失败的资产
            if failed_assets:
                logger.error(f"❌ {len(failed_assets)} 个资产修复失败:")
                for failed_asset in failed_assets:
                    logger.error(f"  - {failed_asset['name']} (ID: {failed_asset['id']}): {failed_asset['error']}")
            
            # 验证修复结果
            logger.info("\n验证修复结果:")
            remaining_assets = Asset.query.filter(
                Asset.status == 2,
                or_(Asset.token_address.is_(None), Asset.token_address == '')
            ).count()
            
            total_approved = Asset.query.filter_by(status=2).count()
            fixed_approved = Asset.query.filter(
                Asset.status == 2,
                Asset.token_address.isnot(None),
                Asset.token_address != ''
            ).count()
            
            logger.info(f"总已通过资产数: {total_approved}")
            logger.info(f"有合约地址的已通过资产数: {fixed_approved}")
            logger.info(f"仍缺少合约地址的已通过资产数: {remaining_assets}")
            
            if remaining_assets == 0:
                logger.info("🎉 所有已通过的资产现在都有合约地址了！")
            
        except Exception as e:
            logger.error(f"修复过程中发生错误: {str(e)}")
            db.session.rollback()
            raise

def main():
    """主函数"""
    try:
        fix_approved_assets_contracts()
        logger.info("脚本执行完成")
    except Exception as e:
        logger.error(f"脚本执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()