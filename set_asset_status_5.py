#!/usr/bin/env python3
"""
将资产20的状态设置为5（支付已确认）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.asset import Asset
from datetime import datetime

def set_asset_status_5():
    app = create_app()
    
    with app.app_context():
        print("=== 将资产20状态设置为5 ===\n")
        
        # 查找资产20
        asset = Asset.query.get(20)
        if not asset:
            print("❌ 资产20不存在")
            return
        
        print(f"📋 资产20当前信息:")
        print(f"   ID: {asset.id}")
        print(f"   名称: {asset.name}")
        print(f"   符号: {asset.token_symbol}")
        print(f"   当前状态: {asset.status}")
        print()
        
        try:
            # 直接使用SQL更新，绕过模型约束
            from sqlalchemy import text
            
            # 更新状态为5
            db.session.execute(
                text("UPDATE assets SET status = 5, updated_at = :updated_at WHERE id = 20"),
                {"updated_at": datetime.utcnow()}
            )
            db.session.commit()
            
            # 重新查询验证
            asset = Asset.query.get(20)
            print(f"✅ 成功更新资产状态:")
            print(f"   新状态: {asset.status}")
            print(f"   更新时间: {asset.updated_at}")
            print()
            
            # 验证自动上链条件
            should_auto_onchain = (
                asset.status == 5 and 
                not asset.token_address and 
                not asset.deployment_in_progress and 
                not asset.deleted_at
            )
            
            if should_auto_onchain:
                print("✅ 资产20现在满足自动上链条件:")
                print("   - 状态为5（支付已确认）")
                print("   - 没有token地址")
                print("   - 没有部署进行中")
                print("   - 没有被删除")
                print()
                print("🔄 自动上链任务应该会在下次执行时处理这个资产（每5分钟执行一次）")
                print("   请等待几分钟后检查上链历史记录")
            else:
                print("❌ 资产20仍不满足自动上链条件")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 更新资产状态失败: {str(e)}")
        
        print("\n=== 更新完成 ===")

if __name__ == '__main__':
    set_asset_status_5() 