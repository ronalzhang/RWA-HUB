#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 获取数据库连接字符串，如果没有则使用默认值
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rwa_hub_user:password@localhost/rwa_hub")

# 创建数据库引擎
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

    def to_dict(self):
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if self.metadata:
            try:
                result['metadata'] = json.loads(self.metadata)
            except:
                pass
        return result

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(String(255), primary_key=True)
    asset_id = Column(String(255), nullable=False)
    buyer_address = Column(String(255), nullable=True)
    seller_address = Column(String(255), nullable=True)
    amount = Column(String(255), nullable=False)
    price = Column(String(255), nullable=False)
    tx_hash = Column(String(255), nullable=True)
    status = Column(String(50), default="pending")
    payment_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if self.payment_details:
            try:
                result['payment_details'] = json.loads(self.payment_details)
            except:
                pass
        return result

def format_asset_info(asset):
    """格式化资产信息输出"""
    asset_dict = asset.to_dict()
    output = [
        f"\n===== 资产详情 =====",
        f"资产ID: {asset_dict['id']}",
        f"资产名称: {asset_dict['name']}",
        f"资产类型: {asset_dict['asset_type']}",
        f"代币符号: {asset_dict['token_symbol']}",
        f"区块链: {asset_dict['blockchain']}",
        f"合约地址: {asset_dict['contract_address']}",
        f"状态: {asset_dict['status']}",
        f"创建时间: {asset_dict['created_at']}",
        f"更新时间: {asset_dict['updated_at']}",
    ]
    
    # 尝试解析和展示元数据
    if isinstance(asset_dict['metadata'], dict):
        metadata = asset_dict['metadata']
        output.append("\n----- 元数据 -----")
        
        if 'issuer_address' in metadata:
            output.append(f"发起人地址: {metadata['issuer_address']}")
        
        if asset_dict['asset_type'].lower() == 'real_estate':
            output.append("\n不动产特有信息:")
            if 'location' in metadata:
                output.append(f"位置: {metadata['location']}")
            if 'area' in metadata:
                output.append(f"面积: {metadata['area']} 平方米")
            if 'property_type' in metadata:
                output.append(f"物业类型: {metadata['property_type']}")
        
        # 显示其他元数据字段
        for key, value in metadata.items():
            if key not in ['issuer_address', 'location', 'area', 'property_type']:
                output.append(f"{key}: {value}")
    
    return "\n".join(output)

def format_trade_info(trade):
    """格式化交易信息输出"""
    trade_dict = trade.to_dict()
    output = [
        f"\n----- 交易记录 -----",
        f"交易ID: {trade_dict['id']}",
        f"购买者地址: {trade_dict['buyer_address']}",
        f"卖家地址: {trade_dict['seller_address']}",
        f"数量: {trade_dict['amount']}",
        f"价格: {trade_dict['price']}",
        f"交易哈希: {trade_dict['tx_hash']}",
        f"状态: {trade_dict['status']}",
        f"创建时间: {trade_dict['created_at']}",
    ]
    
    # 尝试解析和展示支付详情
    if isinstance(trade_dict.get('payment_details'), dict):
        payment = trade_dict['payment_details']
        output.append("\n支付详情:")
        for key, value in payment.items():
            output.append(f"{key}: {value}")
    
    return "\n".join(output)

def query_asset_info(token_symbol):
    """查询资产信息及相关交易"""
    session = Session()
    try:
        # 查询资产信息
        asset = session.query(Asset).filter_by(token_symbol=token_symbol).first()
        
        if not asset:
            print(f"未找到代币符号为 {token_symbol} 的资产")
            return False
        
        # 打印资产详情
        print(format_asset_info(asset))
        
        # 查询相关交易
        trades = session.query(Trade).filter_by(asset_id=asset.id).all()
        
        if trades:
            print(f"\n共找到 {len(trades)} 条交易记录:")
            for trade in trades:
                print(format_trade_info(trade))
        else:
            print("\n该资产暂无交易记录")
        
        return True
    except Exception as e:
        print(f"查询过程中出错: {str(e)}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="查询资产信息及相关交易")
    parser.add_argument("token_symbol", nargs='?', default="RH-108235", help="资产的代币符号")
    
    args = parser.parse_args()
    
    success = query_asset_info(args.token_symbol)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1) 