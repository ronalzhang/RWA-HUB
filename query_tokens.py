from app import app, db
from app.models import Asset

print("Connecting to database...")
with app.app_context():
    tokens = [a.token_symbol for a in Asset.query.all()]
    print(tokens) 