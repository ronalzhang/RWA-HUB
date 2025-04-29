from app import db, create_app
from app.models.asset import Asset
from sqlalchemy import text

# 创建应用实例
app = create_app('development')

with app.app_context():
    # 添加剩余供应量列
    db.session.execute(text('ALTER TABLE assets ADD COLUMN IF NOT EXISTS remaining_supply INTEGER'))
    db.session.commit()
    
    # 初始化剩余供应量数据
    assets = Asset.query.all()
    for asset in assets:
        if asset.remaining_supply is None:
            asset.remaining_supply = asset.token_supply
    
    db.session.commit()
    print('数据库架构更新成功，并初始化了剩余供应量字段') 