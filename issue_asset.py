#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import json
import uuid
import logging
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('issue_asset')

# 加载环境变量
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rwa_hub_user:password@localhost/rwa_hub")
PURCHASE_CONTRACT_ADDRESS = os.getenv("PURCHASE_CONTRACT_ADDRESS", "")

# 初始化数据库连接
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# 定义模型
class Asset(Base):
    __tablename__ = 'assets'
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    asset_type = Column(String(50), nullable=False)
    token_symbol = Column(String(50), nullable=True, unique=True)
    blockchain = Column(String(50), nullable=True)
    contract_address = Column(String(255), nullable=True)
    metadata = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 确保数据库表存在
Base.metadata.create_all(engine)

# 支持的资产类型
ASSET_TYPES = ['real_estate', 'art', 'commodity', 'fund', 'bond', 'stock']
# 支持的区块链
BLOCKCHAINS = ['ethereum', 'solana', 'binance', 'polygon']

def generate_token_symbol(asset_type, name):
    """根据资产类型和名称生成唯一的代币符号"""
    prefix = asset_type[0].upper()
    # 生成随机后缀
    suffix = str(uuid.uuid4().int)[:6]
    return f"{prefix}{name[:2].upper()}-{suffix}"

def create_asset(name, asset_type, description, blockchain, issuer_address, metadata=None):
    """创建新资产"""
    session = Session()
    try:
        # 生成唯一ID
        asset_id = str(uuid.uuid4())
        
        # 生成代币符号
        token_symbol = generate_token_symbol(asset_type, name)
        
        # 准备元数据
        meta_dict = {
            "issuer_address": issuer_address,
            "creation_date": datetime.utcnow().isoformat()
        }
        
        # 合并自定义元数据
        if metadata:
            try:
                if isinstance(metadata, str):
                    meta_dict.update(json.loads(metadata))
                else:
                    meta_dict.update(metadata)
            except json.JSONDecodeError:
                logger.warning("无法解析提供的元数据JSON，将使用默认元数据")
        
        # 创建资产记录
        asset = Asset(
            id=asset_id,
            name=name,
            description=description,
            asset_type=asset_type.lower(),
            token_symbol=token_symbol,
            blockchain=blockchain.lower(),
            metadata=json.dumps(meta_dict, ensure_ascii=False),
            status="pending"
        )
        
        session.add(asset)
        session.commit()
        
        logger.info(f"资产创建成功: ID={asset_id}, 代币符号={token_symbol}")
        return asset
    except Exception as e:
        session.rollback()
        logger.error(f"创建资产失败: {str(e)}")
        raise
    finally:
        session.close()

def display_asset_info(asset):
    """显示资产信息"""
    print("\n===== 新资产已创建 =====")
    print(f"资产ID: {asset.id}")
    print(f"资产名称: {asset.name}")
    print(f"资产类型: {asset.asset_type}")
    print(f"代币符号: {asset.token_symbol}")
    print(f"区块链: {asset.blockchain}")
    print(f"状态: {asset.status}")
    
    # 显示元数据
    if asset.metadata:
        try:
            metadata = json.loads(asset.metadata)
            print("\n----- 元数据 -----")
            for key, value in metadata.items():
                print(f"{key}: {value}")
        except:
            print(f"元数据: {asset.metadata}")

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
    parser.add_argument("--metadata-file", "-m", help="JSON格式的元数据文件路径")
    parser.add_argument("--metadata-json", "-j", help="直接提供JSON格式的元数据")
    
    args = parser.parse_args()
    
    # 处理元数据
    metadata = None
    if args.metadata_file:
        metadata = load_metadata_from_file(args.metadata_file)
    elif args.metadata_json:
        try:
            metadata = json.loads(args.metadata_json)
        except json.JSONDecodeError:
            logger.error("提供的JSON元数据格式无效")
            sys.exit(1)
    
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
        print(f"python query_asset.py {asset.token_symbol}")
        
        sys.exit(0)
    except Exception as e:
        logger.error(f"发行资产时出错: {str(e)}")
        sys.exit(1) 