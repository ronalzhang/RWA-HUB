#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import json
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
logger = logging.getLogger('update_asset_onchain')

# 加载环境变量
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rwa_hub_user:password@localhost/rwa_hub")

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
    meta_data = Column(Text, nullable=True)  # 重命名为meta_data以避免与SQLAlchemy保留字冲突
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 确保数据库表存在
Base.metadata.create_all(engine)

def validate_ethereum_address(address):
    """验证以太坊地址格式"""
    if not address.startswith('0x'):
        raise ValueError("以太坊地址必须以0x开头")
    if len(address) != 42:
        raise ValueError("以太坊地址长度必须为42个字符(包括0x前缀)")
    try:
        # 检查地址是否为有效的十六进制
        int(address[2:], 16)
        return True
    except ValueError:
        raise ValueError("以太坊地址必须是有效的十六进制")

def validate_solana_address(address):
    """验证Solana地址格式"""
    if len(address) != 44 and len(address) != 43:
        raise ValueError("Solana地址长度通常为43或44个字符")
    # 简单的格式检查，实际上还需考虑base58编码验证
    valid_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
    if not all(c in valid_chars for c in address):
        raise ValueError("Solana地址包含无效字符")
    return True

def update_asset_onchain(token_symbol, contract_address, tx_hash=None, status="active"):
    """更新资产的链上信息"""
    session = Session()
    try:
        # 查询资产
        asset = session.query(Asset).filter_by(token_symbol=token_symbol).first()
        
        if not asset:
            logger.error(f"未找到代币符号为 {token_symbol} 的资产")
            return False
        
        # 根据区块链类型验证合约地址
        try:
            if asset.blockchain.lower() == 'ethereum' or asset.blockchain.lower() == 'polygon':
                validate_ethereum_address(contract_address)
            elif asset.blockchain.lower() == 'solana':
                validate_solana_address(contract_address)
        except ValueError as e:
            logger.error(f"合约地址验证失败: {str(e)}")
            return False
        
        # 更新资产信息
        asset.contract_address = contract_address
        asset.status = status
        
        # 更新元数据
        metadata = {}
        if asset.meta_data:
            try:
                metadata = json.loads(asset.meta_data)
            except json.JSONDecodeError:
                logger.warning("无法解析现有元数据，将创建新的元数据")
                metadata = {}
        
        # 添加链上信息到元数据
        metadata["onchain_update_time"] = datetime.utcnow().isoformat()
        if tx_hash:
            metadata["deployment_tx_hash"] = tx_hash
        
        asset.meta_data = json.dumps(metadata, ensure_ascii=False)
        asset.updated_at = datetime.utcnow()
        
        session.commit()
        logger.info(f"资产 {token_symbol} 的链上信息已更新")
        return asset
    except Exception as e:
        session.rollback()
        logger.error(f"更新资产链上信息失败: {str(e)}")
        return False
    finally:
        session.close()

def display_updated_asset(asset):
    """显示更新后的资产信息"""
    print("\n===== 资产已更新 =====")
    print(f"资产ID: {asset.id}")
    print(f"资产名称: {asset.name}")
    print(f"代币符号: {asset.token_symbol}")
    print(f"区块链: {asset.blockchain}")
    print(f"合约地址: {asset.contract_address}")
    print(f"状态: {asset.status}")
    print(f"更新时间: {asset.updated_at}")
    
    # 显示元数据
    if asset.meta_data:
        try:
            metadata = json.loads(asset.meta_data)
            print("\n----- 元数据 -----")
            for key, value in metadata.items():
                print(f"{key}: {value}")
        except:
            print(f"元数据: {asset.meta_data}")

def list_assets(filter_status=None):
    """列出所有资产或按状态筛选资产"""
    session = Session()
    try:
        query = session.query(Asset)
        if filter_status:
            query = query.filter_by(status=filter_status)
        
        assets = query.all()
        
        if not assets:
            print("未找到符合条件的资产")
            return
        
        print(f"\n===== 资产列表 ({len(assets)}) =====")
        for asset in assets:
            print(f"代币符号: {asset.token_symbol}")
            print(f"名称: {asset.name}")
            print(f"类型: {asset.asset_type}")
            print(f"区块链: {asset.blockchain}")
            print(f"状态: {asset.status}")
            print(f"合约地址: {asset.contract_address or '未设置'}")
            print("-" * 50)
    except Exception as e:
        logger.error(f"查询资产列表失败: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="更新资产的链上信息")
    
    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 更新资产命令
    update_parser = subparsers.add_parser('update', help='更新资产的链上信息')
    update_parser.add_argument("--token", "-t", required=True, help="资产的代币符号")
    update_parser.add_argument("--contract", "-c", required=True, help="合约地址")
    update_parser.add_argument("--tx-hash", help="部署交易的哈希值")
    update_parser.add_argument("--status", default="active", choices=["active", "inactive", "pending"],
                              help="资产状态 (默认: active)")
    
    # 列出资产命令
    list_parser = subparsers.add_parser('list', help='列出资产')
    list_parser.add_argument("--status", choices=["active", "inactive", "pending"],
                            help="按状态筛选资产")
    
    args = parser.parse_args()
    
    if args.command == 'update':
        try:
            asset = update_asset_onchain(
                token_symbol=args.token,
                contract_address=args.contract,
                tx_hash=args.tx_hash,
                status=args.status
            )
            
            if asset:
                display_updated_asset(asset)
                print("\n资产链上信息更新成功! 要查询此资产信息，可以运行:")
                print(f"python query_asset.py {asset.token_symbol}")
                sys.exit(0)
            else:
                sys.exit(1)
        except Exception as e:
            logger.error(f"更新资产时出错: {str(e)}")
            sys.exit(1)
    
    elif args.command == 'list':
        list_assets(args.status)
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1) 