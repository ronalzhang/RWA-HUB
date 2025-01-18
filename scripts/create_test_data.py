import os
import random
from datetime import datetime
from app import create_app, db
from app.models.asset import Asset, AssetType, AssetStatus

def generate_eth_address():
    """生成随机以太坊地址"""
    return '0x' + ''.join(random.choices('0123456789abcdef', k=40))

def generate_token_symbol(asset_type, index):
    """生成代币符号"""
    type_code = '10' if asset_type == AssetType.REAL_ESTATE else '20'
    return f'RH-{type_code}{str(index+1).zfill(4)}'

def create_test_data():
    """创建测试数据"""
    app = create_app('development')
    with app.app_context():
        db.create_all()
        
        # 测试数据 - 位置
        locations = [
            '北京市朝阳区建国路88号',
            '上海市浦东新区陆家嘴环路1000号',
            '广州市天河区珠江新城',
            '深圳市南山区科技园',
            '杭州市西湖区文三路'
        ]
        
        # 测试数据 - 名称
        names = [
            '优质商业写字楼',
            '高端住宅公寓',
            '核心商圈商铺',
            '工业园区厂房',
            '城市综合体'
        ]
        
        # 测试数据 - 图片
        images = [
            ['building1.jpg', 'building2.jpg'],
            ['apartment1.jpg', 'apartment2.jpg'],
            ['shop1.jpg', 'shop2.jpg'],
            ['factory1.jpg', 'factory2.jpg'],
            ['complex1.jpg', 'complex2.jpg']
        ]
        
        # 创建5个不动产资产
        for i in range(5):
            asset = Asset(
                name=f'{names[i]} - 不动产',
                asset_type=AssetType.REAL_ESTATE,
                location=locations[i],
                area=random.uniform(1000, 5000),  # 1000-5000平方米
                token_price=random.uniform(100, 1000),  # 100-1000 USDC
                token_symbol=generate_token_symbol(AssetType.REAL_ESTATE, i),
                annual_revenue=random.uniform(3, 8),  # 3-8%
                images={'paths': images[i]},
                documents={'paths': ['proof1.pdf', 'proof2.pdf']},
                status=AssetStatus.APPROVED if i < 3 else AssetStatus.PENDING,
                owner_address=generate_eth_address(),
                creator_address=generate_eth_address()
            )
            db.session.add(asset)
        
        # 创建5个类不动产资产
        for i in range(5):
            asset = Asset(
                name=f'{names[i]} - 类不动产',
                asset_type=AssetType.SEMI_REAL_ESTATE,
                location=locations[i],
                total_value=random.uniform(1000000, 5000000),  # 100-500万USDC
                token_price=random.uniform(10, 100),  # 10-100 USDC
                token_supply=random.randint(10000, 50000),  # 1-5万代币
                token_symbol=generate_token_symbol(AssetType.SEMI_REAL_ESTATE, i),
                annual_revenue=random.uniform(5, 12),  # 5-12%
                images={'paths': images[i]},
                documents={'paths': ['auction1.pdf', 'auction2.pdf']},
                status=AssetStatus.APPROVED if i < 3 else AssetStatus.PENDING,
                owner_address=generate_eth_address(),
                creator_address=generate_eth_address()
            )
            db.session.add(asset)
        
        db.session.commit()
        print("测试数据创建成功！")
        print("- 5个不动产资产 (3个已审核, 2个待审核)")
        print("- 5个类不动产资产 (3个已审核, 2个待审核)")

if __name__ == '__main__':
    create_test_data() 