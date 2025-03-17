from app import create_app, db
from app.models.admin import AdminUser
from datetime import datetime

def setup_admin():
    """创建超级管理员用户"""
    app = create_app()
    
    with app.app_context():
        # 创建超级管理员
        admins_to_create = [
            {
                "wallet_address": "0x123456789012345678901234567890123456abcd",
                "username": "超级管理员",
                "role": "super_admin",
                "permissions": ["管理用户", "管理资产", "管理佣金", "审核资产", "管理设置", "管理管理员", "查看日志", "管理仪表盘"]
            },
            {
                "wallet_address": "EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR",
                "username": "SOL管理员",
                "role": "super_admin",
                "permissions": ["管理用户", "管理资产", "管理佣金", "审核资产", "管理设置", "管理管理员", "查看日志", "管理仪表盘"]
            }
        ]
        
        for admin_data in admins_to_create:
            # 检查是否已存在此管理员
            existing_admin = AdminUser.query.filter_by(wallet_address=admin_data["wallet_address"]).first()
            if existing_admin:
                print(f"已存在管理员: {existing_admin.username} ({existing_admin.wallet_address})")
                continue
            
            # 创建管理员
            admin = AdminUser(
                wallet_address=admin_data["wallet_address"],
                username=admin_data["username"],
                role=admin_data["role"],
                permissions=admin_data["permissions"],
                created_at=datetime.utcnow()
            )
            
            db.session.add(admin)
            db.session.commit()
            print(f"管理员创建成功: {admin.username} ({admin.wallet_address})")

if __name__ == "__main__":
    setup_admin() 