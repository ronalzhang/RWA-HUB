def test_home_page(test_client):
    """测试首页访问"""
    response = test_client.get("/")
    assert response.status_code == 200

def test_assets_page(test_client):
    """测试资产列表页访问"""
    response = test_client.get("/assets")
    assert response.status_code == 200

def test_create_asset_page(test_client):
    """测试资产创建页面访问"""
    response = test_client.get("/assets/create")
    assert response.status_code == 200
