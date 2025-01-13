import pytest
import json
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import io

def test_get_nonce(test_client):
    """测试获取nonce"""
    response = test_client.post("/api/auth/nonce", 
        json={"address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"})
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "nonce" in data
    assert "address" in data

def test_create_asset(test_client, test_files):
    """测试创建资产"""
    # 创建测试账户
    account = Account.create()
    
    # 准备测试数据
    data = {
        "name": "测试资产",
        "asset_type": "10",  # 不动产
        "area": "100",
        "token_price": "0.1",
        "location": "测试地址"
    }
    
    # 准备文件数据
    with open(test_files["image"], "rb") as f:
        image_data = f.read()
    with open(test_files["pdf"], "rb") as f:
        pdf_data = f.read()
    
    # 创建文件对象
    image = (io.BytesIO(image_data), "test.jpg")
    pdf = (io.BytesIO(pdf_data), "test.pdf")
    
    # 发送请求
    response = test_client.post(
        "/api/assets/",
        data={
            **data,
            "images": image,
            "documents": pdf
        }
    )
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert "id" in data
    assert "token_symbol" in data
    assert data["token_symbol"].startswith("RH-01")

def test_get_assets(test_client):
    """测试获取资产列表"""
    response = test_client.get("/api/assets/")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "items" in data
    assert "total" in data
    assert "pages" in data

def test_get_asset_detail(test_client, test_files):
    """测试获取资产详情"""
    # 先创建一个测试资产
    test_create_asset(test_client, test_files)
    
    response = test_client.get("/api/assets/1")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["name"] == "测试资产"
    assert data["token_symbol"].startswith("RH-01")
