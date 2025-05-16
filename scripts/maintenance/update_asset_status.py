#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动更新资产状态，用于修复异常状态。
用法：修改下方ASSET_ID和TARGET_STATUS后运行此脚本
"""

from app import create_app
from app.models import Asset, AssetStatus
from app.extensions import db

# 配置参数
ASSET_ID = None  # 设置要更新的资产ID，例如: 123
TARGET_STATUS = None  # 设置目标状态，使用AssetStatus枚举值，例如: AssetStatus.APPROVED.value

def main():
    """执行主函数"""
    if not ASSET_ID:
        print("错误: 请先设置ASSET_ID参数")
        return
        
    if TARGET_STATUS is None:
        print("错误: 请先设置TARGET_STATUS参数")
        print("可用的状态值:")
        for status in AssetStatus:
            print(f"  - {status.name}: {status.value}")
        return
        
    app = create_app()
    with app.app_context():
        asset = Asset.query.get(ASSET_ID)
        if not asset:
            print(f"错误: 未找到ID为 {ASSET_ID} 的资产")
            return
            
        old_status = asset.status
        old_status_name = next((s.name for s in AssetStatus if s.value == old_status), "未知")
        
        new_status_name = next((s.name for s in AssetStatus if s.value == TARGET_STATUS), "未知")
        
        print(f"资产: {asset.name} (ID: {ASSET_ID})")
        print(f"当前状态: {old_status} ({old_status_name})")
        print(f"目标状态: {TARGET_STATUS} ({new_status_name})")
        
        confirm = input("确认更新？(y/n): ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return
            
        asset.status = TARGET_STATUS
        db.session.commit()
        print(f"资产状态已更新: {old_status}({old_status_name}) -> {TARGET_STATUS}({new_status_name})")

if __name__ == "__main__":
    main()
