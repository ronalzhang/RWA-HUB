from app import create_app
from app.models import Asset
import json

app = create_app('development')

with app.app_context():
    try:
        # 查询最近的5条记录
        print("\n最近的资产记录:")
        print("-" * 80)
        assets = Asset.query.order_by(Asset.id.desc()).limit(5).all()
        for asset in assets:
            print(f"\nID: {asset.id}")
            print(f"名称: {asset.name}")
            print(f"创建时间: {asset.created_at}")
            print(f"资产类型: {asset.asset_type}")
            print(f"状态: {asset.status}")
            print(f"原始图片数据(_images): {asset._images}")
            print(f"处理后的图片(images属性): {asset.images}")
            print("-" * 50)
    except Exception as e:
        print(f"查询失败: {str(e)}")

        # 查询最近的几条记录
        print("\n最近的资产记录:")
        assets = Asset.query.order_by(Asset.id.desc()).limit(3).all()
        for asset in assets:
            print(f"\nID: {asset.id}")
            print(f"名称: {asset.name}")
            print(f"原始图片数据: {asset._images}")
            print("-" * 50) 