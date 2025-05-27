#!/usr/bin/env python3
"""
修复资产deployment状态
"""

import sys
import os
sys.path.append('/root/RWA-HUB')

from app import create_app
from app.models.asset import Asset
from app.extensions import db

def fix_deployment_status():
    app = create_app()
    with app.app_context():
        print('=== 修复资产deployment状态 ===\n')
        
        # 获取所有Payment Confirmed状态的资产
        assets = Asset.query.filter_by(status=5).all()
        print(f'找到 {len(assets)} 个Payment Confirmed状态的资产')
        
        for asset in assets:
            print(f'资产 {asset.id}: deployment_started_at={asset.deployment_started_at}')
            
            # 清理deployment_started_at字段
            asset.deployment_started_at = None
            asset.deployment_in_progress = False
            
            print(f'  ✓ 已清理资产 {asset.id}')
        
        # 提交更改
        db.session.commit()
        print(f'\n✓ 已清理所有 {len(assets)} 个资产的deployment状态')
        
        return len(assets)

if __name__ == "__main__":
    count = fix_deployment_status()
    print(f'\n=== 修复完成，共处理 {count} 个资产 ===') 