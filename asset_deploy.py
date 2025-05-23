#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
手动触发资产上链流程
"""

from app import create_app
from app.blockchain.asset_service import AssetService

def main():
    # 创建应用实例
    app = create_app()
    
    # 使用应用实例的上下文
    with app.app_context():
        try:
            # 实例化资产服务
            service = AssetService()
            
            # 部署资产
            result = service.deploy_asset_to_blockchain(1)
            print(f"上链结果: {result}")
        except Exception as e:
            print(f"上链失败: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main() 