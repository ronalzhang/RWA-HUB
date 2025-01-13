import pytest
import os
import tempfile

@pytest.fixture
def test_client():
    from app import create_app
    
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.test_client() as client:
        yield client

@pytest.fixture
def test_files():
    """提供测试文件路径"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return {
        "image": os.path.join(base_dir, "test_files", "test.jpg"),
        "pdf": os.path.join(base_dir, "test_files", "test.pdf")
    }
