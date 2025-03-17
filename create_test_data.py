from app import create_app
from app.models import DistributionLevel, CommissionSetting
from app.extensions import db

app = create_app()
with app.app_context():
    # 清空现有数据
    DistributionLevel.query.delete()
    CommissionSetting.query.delete()
    
    # 创建分销等级
    levels = [
        DistributionLevel(level=1, commission_rate=5.0, description="一级分销", is_active=True),
        DistributionLevel(level=2, commission_rate=3.0, description="二级分销", is_active=True),
        DistributionLevel(level=3, commission_rate=1.0, description="三级分销", is_active=True)
    ]
    
    # 创建佣金设置
    settings = [
        CommissionSetting(asset_type_id=None, commission_rate=2.5, min_amount=10, max_amount=1000, is_active=True, created_by="EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR"),
        CommissionSetting(asset_type_id=10, commission_rate=3.0, min_amount=20, max_amount=2000, is_active=True, created_by="EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR"),
        CommissionSetting(asset_type_id=20, commission_rate=3.5, min_amount=30, max_amount=3000, is_active=True, created_by="EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR")
    ]
    
    # 添加到数据库
    db.session.add_all(levels)
    db.session.add_all(settings)
    db.session.commit()
    
    print("测试数据创建成功！")
    print('分销等级:', DistributionLevel.query.all())
    print('佣金设置:', CommissionSetting.query.all()) 