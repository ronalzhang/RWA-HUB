from app import create_app
from app.models import Asset
from app.models.asset import AssetStatus

app = create_app('development')
with app.app_context():
    assets = Asset.query.all()
    print(f'总资产数: {len(assets)}')
    for asset in assets:
        print(f'ID: {asset.id}, 名称: {asset.name}, 状态: {asset.status}, 类型: {asset.asset_type}') 