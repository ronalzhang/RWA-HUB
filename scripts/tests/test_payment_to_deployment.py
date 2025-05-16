#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试支付确认到资产上链的流程
使用方法: python scripts/tests/test_payment_to_deployment.py [asset_id]
"""

import sys
import os
import json
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.models import Asset, AssetStatus
from app.blockchain.asset_service import AssetService
from app.extensions import db

def test_payment_to_deployment(asset_id):
    """
    测试支付确认到上链的完整流程
    
    Args:
        asset_id: 要测试的资产ID
    """
    print(f"开始测试资产 {asset_id} 的支付确认到上链流程")
    
    # 创建应用上下文
    app = create_app()
    
    with app.app_context():
        try:
            # 获取资产
            asset = Asset.query.get(asset_id)
            if not asset:
                print(f"错误: 找不到资产 ID: {asset_id}")
                return False
                
            print(f"找到资产: ID={asset_id}, 名称={asset.name}, 状态={asset.status}")
            
            # 检查当前状态
            if asset.token_address:
                print(f"资产已经上链，代币地址: {asset.token_address}")
                return True
                
            if asset.deployment_in_progress:
                print(f"资产正在上链处理中，开始时间: {asset.deployment_started_at}")
                return False
                
            # 准备支付信息
            payment_info = {
                'tx_hash': f"test_tx_{int(time.time())}",
                'confirmed_at': datetime.utcnow().isoformat(),
                'status': 'confirmed',
                'details': {'test': True, 'amount': 1000}
            }
            
            print(f"使用测试支付信息: {payment_info}")
            
            # 设置资产支付信息
            asset.payment_tx_hash = payment_info['tx_hash']
            asset.payment_details = json.dumps(payment_info)
            db.session.commit()
            
            print(f"已更新资产支付信息")
            
            # 调用支付处理
            asset_service = AssetService()
            print(f"开始处理支付...")
            
            result = asset_service.process_asset_payment(asset_id, payment_info)
            print(f"支付处理结果: {result}")
            
            # 检查结果
            asset = Asset.query.get(asset_id)  # 重新查询，获取最新状态
            
            print(f"处理后的资产状态: {asset.status}")
            if asset.token_address:
                print(f"上链成功，代币地址: {asset.token_address}")
                return True
                
            if asset.deployment_in_progress:
                print(f"上链处理中，请稍后检查结果")
                return True
            
            return result.get('success', False)
            
        except Exception as e:
            import traceback
            print(f"测试过程中发生错误: {str(e)}")
            print(traceback.format_exc())
            return False

if __name__ == "__main__":
    # 获取命令行参数
    if len(sys.argv) > 1:
        asset_id = int(sys.argv[1])
    else:
        # 默认使用ID为1的资产
        asset_id = 1
        
    result = test_payment_to_deployment(asset_id)
    
    if result:
        print("测试成功完成")
        sys.exit(0)
    else:
        print("测试失败")
        sys.exit(1) 