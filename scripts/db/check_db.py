from app import create_app
from app.models import DistributionLevel, CommissionSetting

app = create_app()
with app.app_context():
    print('分销等级:', DistributionLevel.query.all())
    print('佣金设置:', CommissionSetting.query.all()) 