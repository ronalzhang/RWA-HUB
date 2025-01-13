from app import create_app, db
from app.models.asset import Asset, AssetType, AssetStatus
from app.models.user import User
import random
import string
from datetime import datetime, UTC

# 测试数据
test_locations = [
    "上海市浦东新区陆家嘴",
    "北京市朝阳区CBD",
    "深圳市南山区科技园",
    "广州市天河区珠江新城",
    "杭州市西湖区",
    "成都市武侯区",
    "重庆市渝中区",
    "南京市鼓楼区",
    "武汉市江汉区",
    "西安市雁塔区"
]

test_names = [
    "阳光大厦", "星河中心", "科技广场", "环球金融中心", "创新大厦",
    "未来城", "智慧园区", "商务中心", "文化广场", "生态园"
]

# 测试图片
test_images = [
    "building1.jpg",
    "building2.jpg",
    "building3.jpg",
    "building4.jpg",
    "building5.jpg"
]

def generate_eth_address():
    """生成随机以太坊地址"""
    return "0x" + "".join(random.choices(string.hexdigits, k=40)).lower()

def generate_token_symbol():
    """生成随机代币符号"""
    type_code = random.choice(["01", "02"])
    asset_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"RH-{type_code}{asset_code}"

def create_test_user():
    """创建测试用户"""
    user = User(
        username="test_user",
        email="test@example.com",
        eth_address=generate_eth_address()
    )
    user.set_password("password123")
    return user

def create_test_data():
    """创建所有测试数据"""
    app = create_app()
    
    with app.app_context():
        # 清空现有数据
        Asset.query.delete()
        User.query.delete()
        db.session.commit()
        
        # 创建测试用户
        test_user = create_test_user()
        db.session.add(test_user)
        db.session.commit()
        print("Successfully created test user!")
        print("Username: test_user")
        print("Password: password123")
        print("ETH Address:", test_user.eth_address)
        
        # 创建20个测试资产
        for i in range(20):
            # 随机选择资产类型
            asset_type = random.choice([AssetType.REAL_ESTATE, AssetType.SEMI_REAL_ESTATE])
            
            # 随机生成面积和价格
            area = round(random.uniform(1000, 10000), 2) if asset_type == AssetType.REAL_ESTATE else None
            token_price = round(random.uniform(100, 1000), 2)
            total_value = round(random.uniform(1000000, 10000000), 2) if asset_type == AssetType.SEMI_REAL_ESTATE else None
            
            # 计算代币发行量
            if asset_type == AssetType.REAL_ESTATE:
                token_supply = int(area * 10000)  # 每平方米10000个代币
            else:
                token_supply = int(total_value / token_price)  # 总价值除以代币价格
            
            # 随机选择1-3张图片
            num_images = random.randint(1, 3)
            images = random.sample(test_images, num_images)
            
            # 创建资产
            asset = Asset(
                name=f"{random.choice(test_names)}{i+1}",
                asset_type=asset_type,
                area=area,
                token_price=token_price,
                token_supply=token_supply,
                location=random.choice(test_locations),
                owner_address=test_user.eth_address,
                token_symbol=generate_token_symbol(),
                total_value=total_value,
                annual_revenue=random.uniform(100000, 1000000),
                contract_address=generate_eth_address()
            )
            asset.images = images
            asset.status = AssetStatus.APPROVED.value  # 设置为已审核状态
            
            db.session.add(asset)
            print(f"Created asset: {asset.name} ({asset.token_symbol})")
        
        # 提交所有更改
        db.session.commit()
        print("\nSuccessfully created 20 test assets!")

if __name__ == "__main__":
    create_test_data() 