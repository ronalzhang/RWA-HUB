#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接从命令行触发资产支付确认流程。
用法: python -m scripts.maintenance.trigger_cmd [资产符号]
例如: python -m scripts.maintenance.trigger_cmd RH-108713
"""

import sys
from app import create_app
from app.models import Asset
from app.tasks import monitor_creation_payment

# 默认资产符号
DEFAULT_SYMBOL = 'RH-108713'  # 修改为当前需要处理的资产符号

def main():
    """执行主函数"""
    # 获取命令行参数，如果提供
    asset_symbol = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SYMBOL
    
    app = create_app()
    with app.app_context():
        asset = Asset.query.filter_by(token_symbol=asset_symbol).first()
        
        if not asset:
            print(f"错误: 未找到资产 {asset_symbol}")
            return
            
        print(f"资产ID: {asset.id}, 名称: {asset.name}, 支付哈希: {asset.payment_tx_hash}")
        
        if not asset.payment_tx_hash:
            print(f"错误: 资产没有支付哈希，无法触发确认任务")
            return
            
        print(f"正在触发支付确认任务...")
        result = monitor_creation_payment(asset.id, asset.payment_tx_hash)
        print(f"任务执行结果: {result}")
        print("支付确认任务处理完成")

if __name__ == "__main__":
    main()
