#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import json
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('update_asset_onchain')

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

# 资产类型映射 - 数值到文本
ASSET_TYPE_TO_TEXT = {
    10: 'real_estate',
    20: 'similar_assets',
    30: 'art',
    40: 'commodity',
    50: 'bond',
    60: 'stock'
}

# 状态码映射
STATUS_MAP = {
    "active": 1,
    "inactive": 0,
    "pending": 2
}

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
    try:
        # 获取数据库会话
        if in_app_environment:
            session = get_db_session()
        else:
            session = Session()
        
        # 查询资产
        asset = session.query(Asset).filter(Asset.token_symbol == token_symbol).first()
        
        if not asset:
            logger.error(f"未找到代币符号为 {token_symbol} 的资产")
            return False
        
        # 获取现有区块链详情
        blockchain_details = {}
        if hasattr(asset, 'blockchain_details') and asset.blockchain_details:
            try:
                blockchain_details = json.loads(asset.blockchain_details)
            except json.JSONDecodeError:
                logger.warning("无法解析现有区块链详情，将创建新的详情")
        
        # 获取区块链类型
        blockchain = blockchain_details.get('blockchain', '').lower()
        
        # 验证合约地址
        try:
            if blockchain == 'ethereum' or blockchain == 'polygon':
                validate_ethereum_address(contract_address)
            elif blockchain == 'solana':
                validate_solana_address(contract_address)
        except ValueError as e:
            logger.error(f"合约地址验证失败: {str(e)}")
            return False
        
        # 更新资产信息
        asset.token_address = contract_address
        
        # 转换状态为数字状态码
        status_code = STATUS_MAP.get(status.lower(), 2)  # 默认为pending (2)
        asset.status = status_code
        
        # 更新区块链详情
        blockchain_details["onchain_update_time"] = datetime.utcnow().isoformat()
        blockchain_details["token_address"] = contract_address
        
        if tx_hash:
            asset.deployment_tx_hash = tx_hash
            blockchain_details["deployment_tx_hash"] = tx_hash
        
        asset.blockchain_details = json.dumps(blockchain_details, ensure_ascii=False)
        asset.updated_at = datetime.utcnow()
        
        session.commit()
        logger.info(f"资产 {token_symbol} 的链上信息已更新")
        return asset
    except Exception as e:
        if 'session' in locals():
            session.rollback()
        logger.error(f"更新资产链上信息失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'session' in locals() and not in_app_environment:
            session.close()

def display_updated_asset(asset):
    """显示更新后的资产信息"""
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
    
    # 获取状态文本
    status_int = asset_dict.get('status')
    if isinstance(status_int, int) or (status_int and str(status_int).isdigit()):
        status_map_reverse = {v: k for k, v in STATUS_MAP.items()}
        status_text = status_map_reverse.get(int(status_int), f"未知状态({status_int})")
    else:
        status_text = str(status_int)
        
    print("\n===== 资产已更新 =====")
    print(f"资产ID: {asset_dict['id']}")
    print(f"资产名称: {asset_dict['name']}")
    print(f"资产类型: {asset_type_text} ({asset_dict['asset_type']})")
    print(f"代币符号: {asset_dict['token_symbol']}")
    print(f"代币地址: {asset_dict.get('token_address', 'N/A')}")
    print(f"状态: {status_text} ({asset_dict['status']})")
    print(f"部署交易哈希: {asset_dict.get('deployment_tx_hash', 'N/A')}")
    print(f"更新时间: {asset_dict['updated_at']}")
    
    # 显示区块链详情
    if asset_dict.get('blockchain_details'):
        try:
            blockchain_details = json.loads(asset_dict['blockchain_details'])
            print("\n----- 区块链详情 -----")
            for key, value in blockchain_details.items():
                print(f"{key}: {value}")
        except:
            print(f"区块链详情: {asset_dict['blockchain_details']}")

def list_assets(filter_status=None):
    """列出所有资产或按状态筛选资产"""
    try:
        # 获取数据库会话
        if in_app_environment:
            session = get_db_session()
        else:
            session = Session()
        
        # 查询资产
        query = session.query(Asset)
        if filter_status:
            # 转换状态文本为状态码
            status_code = STATUS_MAP.get(filter_status.lower())
            if status_code is not None:
                query = query.filter(Asset.status == status_code)
        
        assets = query.all()
        
        if not assets:
            print("未找到符合条件的资产")
            return
        
        print(f"\n===== 资产列表 ({len(assets)}) =====")
        for asset in assets:
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
            
            # 获取状态文本
            status_int = asset_dict.get('status')
            if isinstance(status_int, int) or (status_int and str(status_int).isdigit()):
                status_map_reverse = {v: k for k, v in STATUS_MAP.items()}
                status_text = status_map_reverse.get(int(status_int), f"未知状态({status_int})")
            else:
                status_text = str(status_int)
                
            print(f"代币符号: {asset_dict['token_symbol']}")
            print(f"名称: {asset_dict['name']}")
            print(f"类型: {asset_type_text} ({asset_dict['asset_type']})")
            
            # 尝试获取区块链信息
            blockchain = "未知"
            if asset_dict.get('blockchain_details'):
                try:
                    details = json.loads(asset_dict['blockchain_details'])
                    blockchain = details.get('blockchain', '未知')
                except:
                    pass
                    
            print(f"区块链: {blockchain}")
            print(f"状态: {status_text} ({asset_dict['status']})")
            print(f"代币地址: {asset_dict.get('token_address', '未设置')}")
            print("-" * 50)
    except Exception as e:
        logger.error(f"查询资产列表失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if 'session' in locals() and not in_app_environment:
            session.close()

def fix_asset_onchain_issue():
    app = create_app()
    with app.app_context():
        print('=== 最终修复资产上链问题 ===\n')
        
        # 获取所有Payment Confirmed状态的资产
        assets = Asset.query.filter_by(status=5).all()
        print(f'找到 {len(assets)} 个Payment Confirmed状态的资产')
        
        for asset in assets:
            print(f'资产 {asset.id}: {asset.asset_id}')
            print(f'  - deployment_in_progress: {asset.deployment_in_progress}')
            print(f'  - deployment_started_at: {asset.deployment_started_at}')
            print(f'  - token_address: {asset.token_address}')
            
            # 强制清理所有上链相关字段
            asset.deployment_in_progress = False
            asset.deployment_started_at = None
            asset.deployment_tx_hash = None
            
            print(f'  ✓ 已清理资产 {asset.id} 的上链状态')
        
        # 提交更改
        db.session.commit()
        print(f'\n✓ 已清理所有 {len(assets)} 个资产的上链状态')
        print('\n请重启应用以使更改生效：')
        print('pm2 restart rwa-hub')
        
        return len(assets)

if __name__ == "__main__":
    count = fix_asset_onchain_issue()
    print(f'\n=== 修复完成，共处理 {count} 个资产 ===') 