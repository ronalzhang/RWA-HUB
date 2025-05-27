#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.asset import Asset
from app.models.admin import OnchainHistory

def monitor_asset(asset_symbol='RH-203906'):
    app = create_app()
    with app.app_context():
        asset = Asset.query.filter_by(token_symbol=asset_symbol).first()
        if not asset:
            print(f"未找到资产 {asset_symbol}")
            return
            
        print(f"📊 资产 {asset_symbol} 状态监控:")
        print(f"  状态: {asset.status}")
        print(f"  Token地址: {asset.token_address}")
        print(f"  部署进行中: {asset.deployment_in_progress}")
        print(f"  部署交易哈希: {asset.deployment_tx_hash}")
        
        history = OnchainHistory.query.filter_by(asset_id=asset.id).all()
        print(f"  上链历史记录: {len(history)} 条")
        for h in history:
            print(f"    - 状态: {h.status}, 触发类型: {h.trigger_type}")
            if h.transaction_hash:
                print(f"      交易哈希: {h.transaction_hash}")
            if h.error_message:
                print(f"      错误信息: {h.error_message}")

if __name__ == "__main__":
    monitor_asset() 