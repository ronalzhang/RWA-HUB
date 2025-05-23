#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
手动设置资产上链状态
"""

import sys
from flask import Flask
from app.config import Config
from app.extensions import db
from app.models.asset import Asset, AssetStatus
from app.blockchain.asset_service import AssetService
import datetime
import json
import traceback
import random
import string

def generate_valid_solana_address():
    """生成一个符合验证规则的Solana模拟地址"""
    # Solana地址是base58编码，包含数字1-9和字母，不包含0,O,I,l
    valid_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    # 生成44个字符长度的地址
    return ''.join(random.choice(valid_chars) for _ in range(44))

def force_onchain_status(asset_id):
    """强制将资产状态设置为ON_CHAIN(上链)"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        asset = Asset.query.get(asset_id)
        if not asset:
            print(f"错误: 未找到ID为 {asset_id} 的资产")
            return False
            
        print(f"资产 {asset_id} ({asset.token_symbol}) 当前详情:")
        print(f"状态码: {asset.status}")
        
        # 查找状态名称
        status_name = "未知"
        for status in AssetStatus:
            if status.value == asset.status:
                status_name = status.name
                break
        
        print(f"状态: {status_name}")
        print(f"支付确认: {asset.payment_confirmed}")
        print(f"上链地址: {asset.token_address}")
            
        # 强制设置为ON_CHAIN状态(值为2)
        print("强制更新资产状态为ON_CHAIN(已上链)...")
        asset.payment_confirmed = True
        asset.payment_confirmed_at = datetime.datetime.utcnow()
        asset.status = AssetStatus.ON_CHAIN.value  # 直接设置为ON_CHAIN，值为2
        
        # 设置模拟的token地址
        if not asset.token_address:
            # 生成一个符合验证规则的Solana地址
            asset.token_address = generate_valid_solana_address()
            print(f"已生成模拟token地址: {asset.token_address}")
        
        # 确保没有处理中的标志
        asset.deployment_in_progress = False
        
        # 更新payment_details
        details = json.loads(asset.payment_details) if asset.payment_details else {}
        details['status'] = 'on_chain'
        details['confirmed_at'] = asset.payment_confirmed_at.isoformat()
        details['force_updated'] = True
        details['on_chain_at'] = datetime.datetime.utcnow().isoformat()
        asset.payment_details = json.dumps(details)
        
        try:
            db.session.commit()
            print(f"资产 {asset_id} 已强制更新为 ON_CHAIN 状态(值:{AssetStatus.ON_CHAIN.value})，模拟上链完成")
            return True
        except Exception as e:
            print(f"更新数据库状态失败: {str(e)}")
            print(traceback.format_exc())
            db.session.rollback()
            return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python3 update_payment.py <资产ID>")
        sys.exit(1)
        
    try:
        asset_id = int(sys.argv[1])
    except ValueError:
        print("错误: 资产ID必须是整数")
        sys.exit(1)
        
    success = force_onchain_status(asset_id)
    sys.exit(0 if success else 1) 