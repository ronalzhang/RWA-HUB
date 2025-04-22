#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import json
from datetime import datetime

# 检查是否在应用内运行
in_app_environment = True
try:
    # 设置路径和环境变量
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    if os.path.exists(os.path.join(app_path, 'app')):
        sys.path.append(app_path)
        os.environ['FLASK_ENV'] = 'development'
        
        # 尝试导入应用模型
        from app.models.asset import Asset
        from app.models.trade import Trade
        from app.utils.db import get_db_session
        print("使用RWA-HUB应用内置模型")
    else:
        in_app_environment = False
except ImportError:
    in_app_environment = False

# 如果不在应用内，则使用独立模型
if not in_app_environment:
    print("未能导入应用模型，使用独立模型")
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

# 资产类型映射
ASSET_TYPE_MAP = {
    10: 'real_estate',
    20: 'similar_assets',
    30: 'art',
    40: 'commodity',
    50: 'bond',
    60: 'stock'
}

def format_asset_info(asset):
    """格式化资产信息输出"""
    asset_dict = {}
    for c in asset.__table__.columns:
        value = getattr(asset, c.name)
        asset_dict[c.name] = value
        
    # 获取资产类型的文本描述
    asset_type_value = asset_dict.get('asset_type')
    if isinstance(asset_type_value, int) or asset_type_value and asset_type_value.isdigit():
        asset_type_int = int(asset_type_value)
        asset_type_text = ASSET_TYPE_MAP.get(asset_type_int, f"未知类型({asset_type_int})")
    else:
        asset_type_text = str(asset_type_value)
    
    output = [
        f"\n===== 资产详情 =====",
        f"资产ID: {asset_dict['id']}",
        f"资产名称: {asset_dict['name']}",
        f"资产类型: {asset_type_text} ({asset_dict['asset_type']})",
        f"代币符号: {asset_dict['token_symbol']}",
        f"代币价格: {asset_dict.get('token_price', 'N/A')}",
        f"代币总供应量: {asset_dict.get('token_supply', 'N/A')}",
        f"剩余供应量: {asset_dict.get('remaining_supply', 'N/A')}",
        f"代币地址: {asset_dict.get('token_address', 'N/A')}",
        f"创建者地址: {asset_dict.get('creator_address', 'N/A')}",
        f"状态: {asset_dict['status']}",
        f"创建时间: {asset_dict['created_at']}",
        f"更新时间: {asset_dict['updated_at']}",
    ]
    
    # 如果是不动产，显示相关字段
    if asset_type_text == 'real_estate' and asset_dict.get('location'):
        output.extend([
            f"\n----- 不动产信息 -----",
            f"位置: {asset_dict.get('location', 'N/A')}",
            f"面积: {asset_dict.get('area', 'N/A')}",
            f"总价值: {asset_dict.get('total_value', 'N/A')}",
            f"年收益率: {asset_dict.get('annual_revenue', 'N/A')}"
        ])
    
    # 展示区块链详情
    if asset_dict.get('blockchain_details'):
        try:
            blockchain_details = json.loads(asset_dict['blockchain_details'])
            output.append("\n----- 区块链详情 -----")
            for key, value in blockchain_details.items():
                output.append(f"{key}: {value}")
        except:
            output.append(f"区块链详情: {asset_dict['blockchain_details']}")
    
    # 展示图片和文档
    if asset_dict.get('images'):
        try:
            images = json.loads(asset_dict['images'])
            output.append("\n----- 图片 -----")
            for i, img in enumerate(images):
                output.append(f"图片 {i+1}: {img}")
        except:
            output.append(f"图片: {asset_dict['images']}")
    
    if asset_dict.get('documents'):
        try:
            documents = json.loads(asset_dict['documents'])
            output.append("\n----- 文档 -----")
            for i, doc in enumerate(documents):
                output.append(f"文档 {i+1}: {doc}")
        except:
            output.append(f"文档: {asset_dict['documents']}")
    
    return "\n".join(output)

def format_trade_info(trade):
    """格式化交易信息输出"""
    trade_dict = {}
    for c in trade.__table__.columns:
        value = getattr(trade, c.name)
        trade_dict[c.name] = value
        
    output = [
        f"\n----- 交易记录 -----",
        f"交易ID: {trade_dict['id']}",
        f"购买者地址: {trade_dict['buyer_address']}",
        f"卖家地址: {trade_dict.get('seller_address', 'N/A')}",
        f"数量: {trade_dict['amount']}",
        f"价格: {trade_dict['price']}",
        f"交易哈希: {trade_dict.get('tx_hash', 'N/A')}",
        f"状态: {trade_dict['status']}",
        f"创建时间: {trade_dict['created_at']}",
    ]
    
    # 尝试解析和展示支付详情
    if trade_dict.get('payment_details'):
        try:
            payment_details = json.loads(trade_dict['payment_details'])
            output.append("\n支付详情:")
            for key, value in payment_details.items():
                output.append(f"{key}: {value}")
        except:
            output.append(f"支付详情: {trade_dict['payment_details']}")
    
    return "\n".join(output)

def query_asset_info(token_symbol):
    """查询资产信息及相关交易"""
    try:
        # 获取数据库会话
        if in_app_environment:
            session = get_db_session()
        else:
            session = Session()
            
        # 查询资产信息
        asset = session.query(Asset).filter(Asset.token_symbol == token_symbol).first()
        
        if not asset:
            print(f"未找到代币符号为 {token_symbol} 的资产")
            return False
        
        # 打印资产详情
        print(format_asset_info(asset))
        
        # 查询相关交易
        trades = session.query(Trade).filter(Trade.asset_id == asset.id).all()
        
        if trades:
            print(f"\n共找到 {len(trades)} 条交易记录:")
            for trade in trades:
                print(format_trade_info(trade))
        else:
            print("\n该资产暂无交易记录")
        
        return True
    except Exception as e:
        print(f"查询过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if not in_app_environment:
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