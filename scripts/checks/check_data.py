from app import create_app, db
from app.models.asset import Asset
from app.models.dividend import DividendRecord

app = create_app()
with app.app_context():
    # 获取一些资产示例
    assets = Asset.query.limit(3).all()
    print("\n===== 资产示例 =====")
    for asset in assets:
        print(f"ID: {asset.id}, 名称: {asset.name}, 代币符号: {asset.token_symbol}")
    
    # 获取一些分红记录示例
    dividends = DividendRecord.query.limit(3).all()
    print("\n===== 分红记录示例 =====")
    if dividends:
        for div in dividends:
            print(f"ID: {div.id}, 资产ID: {div.asset_id}, 金额: {div.amount}")
    else:
        print("没有找到分红记录")
        
    # 尝试获取具有完整关联的示例
    print("\n===== 资产及其关联的分红记录 =====")
    asset_with_dividends = Asset.query.join(DividendRecord).first()
    if asset_with_dividends:
        print(f"资产ID: {asset_with_dividends.id}, 名称: {asset_with_dividends.name}")
        for div in asset_with_dividends.dividend_records:
            print(f"  - 分红ID: {div.id}, 金额: {div.amount}, 日期: {div.created_at}")
    else:
        print("没有找到具有分红记录的资产")
