from app import create_app, db
from app.models.asset import Asset

app = create_app()
with app.app_context():
    columns = Asset.__table__.columns
    print('===== Assets表字段 =====')
    for column in columns:
        print(f'- {column.name}: {column.type} (nullable={column.nullable})')
