import pytest
from datetime import datetime
from app.models.asset import Asset, AssetType

def test_create_real_estate_asset():
    """测试创建不动产资产"""
    asset = Asset(
        name="测试不动产",
        asset_type=AssetType.REAL_ESTATE,
        area=100,
        token_price=0.1,
        location="北京市朝阳区",
        owner_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        token_symbol="RH-011234",
        images=["ipfs://QmTest1"],
        documents=["ipfs://QmTest2", "ipfs://QmTest3"]
    )
    
    assert asset.name == "测试不动产"
    assert asset.asset_type == AssetType.REAL_ESTATE
    assert asset.area == 100
    assert asset.token_price == 0.1
    assert asset.token_supply == 1000000  # area * 10000
    assert asset.token_symbol.startswith("RH-01")
    assert len(asset.images) == 1
    assert len(asset.documents) == 2

def test_create_non_real_estate_asset():
    """测试创建类不动产资产"""
    asset = Asset(
        name="测试艺术品",
        asset_type=AssetType.NON_REAL_ESTATE,
        total_value=1000000,
        token_price=1.0,
        token_supply=100000,
        location="上海市黄浦区",
        owner_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        token_symbol="RH-021234",
        images=["ipfs://QmTest1"],
        documents=["ipfs://QmTest2"]
    )
    
    assert asset.name == "测试艺术品"
    assert asset.asset_type == AssetType.NON_REAL_ESTATE
    assert asset.total_value == 1000000
    assert asset.token_price == 1.0
    assert asset.token_supply == 100000
    assert asset.token_symbol.startswith("RH-02")
    assert len(asset.images) == 1
    assert len(asset.documents) == 1

def test_asset_validation():
    """测试资产验证"""
    # 测试必填字段
    with pytest.raises(ValueError):
        Asset(
            name="",  # 空名称
            asset_type=AssetType.REAL_ESTATE,
            area=100,
            token_price=0.1,
            location="北京市朝阳区",
            owner_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        )
    
    # 测试面积验证
    with pytest.raises(ValueError):
        Asset(
            name="测试不动产",
            asset_type=AssetType.REAL_ESTATE,
            area=-1,  # 负面积
            token_price=0.1,
            location="北京市朝阳区",
            owner_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        )
    
    # 测试代币价格验证
    with pytest.raises(ValueError):
        Asset(
            name="测试不动产",
            asset_type=AssetType.REAL_ESTATE,
            area=100,
            token_price=0,  # 零价格
            location="北京市朝阳区",
            owner_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        )

def test_asset_to_dict():
    """测试资产序列化"""
    asset = Asset(
        name="测试不动产",
        asset_type=AssetType.REAL_ESTATE,
        area=100,
        token_price=0.1,
        location="北京市朝阳区",
        owner_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        token_symbol="RH-011234",
        images=["ipfs://QmTest1"],
        documents=["ipfs://QmTest2", "ipfs://QmTest3"]
    )
    
    data = asset.to_dict()
    assert data["name"] == "测试不动产"
    assert data["asset_type"] == AssetType.REAL_ESTATE.value
    assert data["area"] == 100
    assert data["token_price"] == 0.1
    assert data["token_supply"] == 1000000
    assert data["token_symbol"] == "RH-011234"
    assert len(data["images"]) == 1
    assert len(data["documents"]) == 2

def test_asset_from_dict():
    """测试资产反序列化"""
    data = {
        "name": "测试不动产",
        "asset_type": AssetType.REAL_ESTATE.value,
        "area": 100,
        "token_price": 0.1,
        "location": "北京市朝阳区",
        "owner_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        "token_symbol": "RH-011234",
        "images": ["ipfs://QmTest1"],
        "documents": ["ipfs://QmTest2", "ipfs://QmTest3"],
        "created_at": datetime.now().isoformat()
    }
    
    asset = Asset.from_dict(data)
    assert asset.name == "测试不动产"
    assert asset.asset_type == AssetType.REAL_ESTATE
    assert asset.area == 100
    assert asset.token_price == 0.1
    assert asset.token_supply == 1000000
    assert asset.token_symbol == "RH-011234"
    assert len(asset.images) == 1
    assert len(asset.documents) == 2
