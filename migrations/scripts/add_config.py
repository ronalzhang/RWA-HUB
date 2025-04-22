from app import create_app
from app.models.admin import SystemConfig
from app import db

app = create_app()
with app.app_context():
    config = SystemConfig.query.filter_by(config_key="PURCHASE_CONTRACT_ADDRESS").first()
    if not config:
        config = SystemConfig(
            config_key="PURCHASE_CONTRACT_ADDRESS", 
            config_value="9AcvoQmz22KRcMhkLkeSkKs8W7ru6oae8GHcxrS83fKz",
            description="Purchase contract address for token trading"
        )
        db.session.add(config)
        db.session.commit()
        print("Added new config")
    else:
        config.config_value = "9AcvoQmz22KRcMhkLkeSkKs8W7ru6oae8GHcxrS83fKz"
        db.session.commit()
        print("Updated existing config")
    print(f"Current config value: {config.config_value}")