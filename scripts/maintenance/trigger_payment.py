#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动触发资产支付确认任务。
用法：修改下方ASSET_ID和TX_HASH后运行此脚本
"""

from app import create_app
from app.models import Asset
from app.tasks import monitor_creation_payment

# 配置参数
ASSET_ID = None  # 设置要处理的资产ID，例如: 123
TX_HASH = None   # 设置要确认的交易哈希，例如: "abc123..."

def main():
    """执行主函数"""
    if not ASSET_ID:
        print("错误: 请先设置ASSET_ID参数")
        return
        
    app = create_app()
    with app.app_context():
        if TX_HASH:
            # 使用提供的交易哈希
            print(f"正在处理资产 ID: {ASSET_ID}, 交易哈希: {TX_HASH}")
            monitor_creation_payment(ASSET_ID, TX_HASH)
        else:
            # 使用资产当前的交易哈希
            asset = Asset.query.get(ASSET_ID)
            if not asset:
                print(f"错误: 未找到ID为 {ASSET_ID} 的资产")
                return
                
            if not asset.payment_tx_hash:
                print(f"错误: 资产 {ASSET_ID} 没有支付交易哈希")
                return
                
            print(f"正在处理资产 ID: {ASSET_ID}, 交易哈希: {asset.payment_tx_hash}")
            monitor_creation_payment(ASSET_ID, asset.payment_tx_hash)
            
        print("支付确认任务已触发")

if __name__ == "__main__":
    main()
