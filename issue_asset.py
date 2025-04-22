#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import json
import uuid
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('issue_asset')

# 检查是否在应用内运行
in_app_environment = True
try:
    # 设置路径和环境变量
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    if os.path.exists(os.path.join(app_path, 'app')):
        sys.path.append(app_path)
        os.environ['FLASK_ENV'] = 'development'
        
        # 尝试导入应用模型和工具
        from app.models.asset import Asset
        from app.utils.db import get_db_session
        from app.utils.common import generate_id
        logger.info("使用RWA-HUB应用内置模型")
    else:
        in_app_environment = False
except ImportError:
    in_app_environment = False

# 如果不在应用内，则使用独立模型
if not in_app_environment:
    logger.info("未能导入应用模型，使用独立模型")
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, Column, String, Text, DateTime
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    
    # 加载环境变量
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rwa_hub_user:password@localhost/rwa_hub")
    
    # 初始化数据库连接
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    Base = declarative_base()
    
    # 定义模型 - 确保与应用模型结构一致
    class Asset(Base):
        __tablename__ = 'assets'
        
        id = Column(String(255), primary_key=True)
        name = Column(String(255), nullable=False)
        description = Column(Text, nullable=True)
        asset_type = Column(String(50), nullable=False)
        location = Column(String(255), nullable=True)
        area = Column(String(50), nullable=True)
        total_value = Column(String(50), nullable=True)
        token_symbol = Column(String(50), nullable=True, unique=True)
        token_price = Column(String(50), nullable=True)
        token_supply = Column(String(50), nullable=True)
        token_address = Column(String(255), nullable=True)
        annual_revenue = Column(String(50), nullable=True)
        images = Column(Text, nullable=True)
        documents = Column(Text, nullable=True)
        status = Column(String(50), default="pending")
        reject_reason = Column(Text, nullable=True)
        owner_address = Column(String(255), nullable=True)
        creator_address = Column(String(255), nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        deleted_at = Column(DateTime, nullable=True)
        remaining_supply = Column(String(50), nullable=True)
        blockchain_details = Column(Text, nullable=True)
        deployment_tx_hash = Column(String(255), nullable=True)
        payment_details = Column(Text, nullable=True)
        payment_confirmed = Column(String(10), default="false")
        payment_confirmed_at = Column(DateTime, nullable=True)
        approved_at = Column(DateTime, nullable=True)
        approved_by = Column(String(255), nullable=True)
    
    # 确保数据库表存在
    Base.metadata.create_all(engine)
    
    # 定义生成ID的函数
    def generate_id():
        return str(uuid.uuid4())

# 资产类型映射 - 文本到数值
ASSET_TYPE_TO_CODE = {
    'real_estate': 10,
    'fund': 20,
    'art': 30,
    'commodity': 40,
    'bond': 50,
    'stock': 60
}

# 资产类型映射 - 数值到文本
ASSET_TYPE_TO_TEXT = {
    10: 'real_estate',
    20: 'fund',
    30: 'art',
    40: 'commodity',
    50: 'bond',
    60: 'stock'
}

# 支持的资产类型
ASSET_TYPES = list(ASSET_TYPE_TO_CODE.keys())
# 支持的区块链
BLOCKCHAINS = ['ethereum', 'solana', 'binance', 'polygon']

def generate_token_symbol(asset_type, name):
    """根据资产类型和名称生成唯一的代币符号"""
    # 获取资产类型的第一个字母
    if isinstance(asset_type, int):
        text_type = ASSET_TYPE_TO_TEXT.get(asset_type, "unknown")
        prefix = text_type[0].upper()
    else:
        prefix = asset_type[0].upper()
        
    # 生成随机后缀
    suffix = str(uuid.uuid4().int)[:6]
    return f"R{prefix}-{suffix}"

def create_asset(name, asset_type, description, blockchain, issuer_address, metadata=None):
    """创建新资产"""
    try:
        # 获取数据库会话
        if in_app_environment:
            session = get_db_session()
        else:
            session = Session()
        
        # 生成唯一ID
        asset_id = generate_id()
        
        # 资产类型转换为数值
        if isinstance(asset_type, str) and asset_type.lower() in ASSET_TYPE_TO_CODE:
            asset_type_code = ASSET_TYPE_TO_CODE[asset_type.lower()]
        elif isinstance(asset_type, int) and asset_type in ASSET_TYPE_TO_TEXT:
            asset_type_code = asset_type
        else:
            asset_type_code = 10  # 默认为不动产
        
        # 生成代币符号
        token_symbol = generate_token_symbol(asset_type_code, name)
        
        # 解析元数据
        meta_dict = {}
        if metadata:
            try:
                if isinstance(metadata, str):
                    meta_dict = json.loads(metadata)
                else:
                    meta_dict = metadata
            except json.JSONDecodeError:
                logger.warning("无法解析提供的元数据JSON，将使用空元数据")
        
        # 提取特定字段
        location = meta_dict.get('location', '')
        area = meta_dict.get('area', '')
        total_value = meta_dict.get('total_value', '')
        annual_revenue = meta_dict.get('annual_revenue', '')
        token_price = meta_dict.get('token_price', '0')
        token_supply = meta_dict.get('token_supply', '0')
        
        # 处理区块链信息
        blockchain_details = {
            "blockchain": blockchain.lower(),
            "issuer_address": issuer_address,
            "creation_date": datetime.utcnow().isoformat()
        }
        
        # 创建资产记录
        asset = Asset(
            id=asset_id,
            name=name,
            description=description,
            asset_type=asset_type_code,
            token_symbol=token_symbol,
            location=location,
            area=area,
            total_value=total_value,
            annual_revenue=annual_revenue,
            token_price=token_price,
            token_supply=token_supply,
            remaining_supply=token_supply,
            creator_address=issuer_address,
            owner_address=issuer_address,
            blockchain_details=json.dumps(blockchain_details, ensure_ascii=False),
            status="pending"
        )
        
        session.add(asset)
        session.commit()
        
        logger.info(f"资产创建成功: ID={asset_id}, 代币符号={token_symbol}")
        return asset
    except Exception as e:
        if 'session' in locals():
            session.rollback()
        logger.error(f"创建资产失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if 'session' in locals() and not in_app_environment:
            session.close()

def display_asset_info(asset):
    """显示资产信息"""
    asset_dict = {}
    for c in asset.__table__.columns:
        value = getattr(asset, c.name)
        asset_dict[c.name] = value
    
    # 获取资产类型的文本描述
    asset_type_value = asset_dict.get('asset_type')
    if isinstance(asset_type_value, int) or (asset_type_value and str(asset_type_value).isdigit()):
        asset_type_int = int(asset_type_value)
        asset_type_text = ASSET_TYPE_TO_TEXT.get(asset_type_int, f"未知类型({asset_type_int})")
    else:
        asset_type_text = str(asset_type_value)
    
    print("\n===== 新资产已创建 =====")
    print(f"资产ID: {asset_dict['id']}")
    print(f"资产名称: {asset_dict['name']}")
    print(f"资产类型: {asset_type_text} ({asset_dict['asset_type']})")
    print(f"代币符号: {asset_dict['token_symbol']}")
    print(f"状态: {asset_dict['status']}")
    
    if asset_type_text == 'real_estate':
        print(f"\n----- 不动产信息 -----")
        print(f"位置: {asset_dict.get('location', 'N/A')}")
        print(f"面积: {asset_dict.get('area', 'N/A')}")
        print(f"总价值: {asset_dict.get('total_value', 'N/A')}")
        print(f"年收益率: {asset_dict.get('annual_revenue', 'N/A')}")
    
    print(f"\n----- 代币信息 -----")
    print(f"代币价格: {asset_dict.get('token_price', 'N/A')}")
    print(f"代币总供应量: {asset_dict.get('token_supply', 'N/A')}")
    print(f"剩余供应量: {asset_dict.get('remaining_supply', 'N/A')}")
    
    if asset_dict.get('blockchain_details'):
        try:
            blockchain_details = json.loads(asset_dict['blockchain_details'])
            print("\n----- 区块链信息 -----")
            for key, value in blockchain_details.items():
                print(f"{key}: {value}")
        except:
            print(f"区块链信息: {asset_dict['blockchain_details']}")

def validate_asset_type(value):
    """验证资产类型是否支持"""
    if value.lower() not in [t.lower() for t in ASSET_TYPES]:
        raise argparse.ArgumentTypeError(
            f"不支持的资产类型: {value}. 支持的类型: {', '.join(ASSET_TYPES)}"
        )
    return value.lower()

def validate_blockchain(value):
    """验证区块链是否支持"""
    if value.lower() not in [b.lower() for b in BLOCKCHAINS]:
        raise argparse.ArgumentTypeError(
            f"不支持的区块链: {value}. 支持的区块链: {', '.join(BLOCKCHAINS)}"
        )
    return value.lower()

def load_metadata_from_file(file_path):
    """从文件加载元数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"无法加载元数据文件 {file_path}: {str(e)}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="发行新资产")
    parser.add_argument("--name", "-n", required=True, help="资产名称")
    parser.add_argument(
        "--type", "-t", required=True, type=validate_asset_type,
        help=f"资产类型, 支持的类型: {', '.join(ASSET_TYPES)}"
    )
    parser.add_argument("--description", "-d", help="资产描述")
    parser.add_argument(
        "--blockchain", "-b", required=True, type=validate_blockchain,
        help=f"区块链平台, 支持的区块链: {', '.join(BLOCKCHAINS)}"
    )
    parser.add_argument("--issuer", "-i", required=True, help="发行人区块链地址")
    parser.add_argument("--location", "-l", help="资产位置 (适用于不动产)")
    parser.add_argument("--area", "-a", help="面积 (适用于不动产)")
    parser.add_argument("--value", "-v", help="总价值")
    parser.add_argument("--revenue", "-r", help="年收益率 (百分比)")
    parser.add_argument("--price", "-p", help="代币单价")
    parser.add_argument("--supply", "-s", help="代币总供应量")
    parser.add_argument("--metadata-file", "-m", help="JSON格式的元数据文件路径")
    parser.add_argument("--metadata-json", "-j", help="直接提供JSON格式的元数据")
    
    args = parser.parse_args()
    
    # 处理元数据
    metadata = {}
    
    # 添加命令行参数中的元数据
    if args.location:
        metadata['location'] = args.location
    if args.area:
        metadata['area'] = args.area
    if args.value:
        metadata['total_value'] = args.value
    if args.revenue:
        metadata['annual_revenue'] = args.revenue
    if args.price:
        metadata['token_price'] = args.price
    if args.supply:
        metadata['token_supply'] = args.supply
    
    # 加载文件或JSON字符串中的元数据
    file_metadata = None
    if args.metadata_file:
        file_metadata = load_metadata_from_file(args.metadata_file)
    elif args.metadata_json:
        try:
            file_metadata = json.loads(args.metadata_json)
        except json.JSONDecodeError:
            logger.error("提供的JSON元数据格式无效")
            sys.exit(1)
    
    # 合并元数据
    if file_metadata:
        metadata.update(file_metadata)
    
    try:
        # 创建资产
        asset = create_asset(
            name=args.name,
            asset_type=args.type,
            description=args.description or "",
            blockchain=args.blockchain,
            issuer_address=args.issuer,
            metadata=metadata
        )
        
        # 显示资产信息
        display_asset_info(asset)
        
        print("\n资产发行成功! 要查询此资产信息，可以运行:")
        print(f"rwa-tool query_asset {asset.token_symbol}")
        
        sys.exit(0)
    except Exception as e:
        logger.error(f"发行资产时出错: {str(e)}")
        sys.exit(1) 