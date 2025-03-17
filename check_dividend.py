from app import create_app, db
from app.models.dividend import DividendRecord

app = create_app()
with app.app_context():
    columns = DividendRecord.__table__.columns
    print("===== DividendRecord表字段 =====")
    for column in columns:
        print(f"- {column.name}: {column.type} (nullable={column.nullable})")
    print("\n===== DividendRecord外键 =====")
    for fk in DividendRecord.__table__.foreign_keys:
        print(f"- {fk.parent} 指向 {fk.target_fullname}")
