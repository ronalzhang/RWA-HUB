from app import create_app, db

def init_database():
    """Initialize the database by creating all tables."""
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    init_database() 