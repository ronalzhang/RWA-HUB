#!/usr/bin/env python3
"""
检查资产29的当前状态
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Asset, OnchainHistory
from app.extensions import db
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_asset_29_status():
    """检查资产29的状态"""
    app = create_app()
    
    with app.app_context():
        try:
            # 查询资产29
            asset = Asset.query.filter_by(id=29).first()
            if not asset:
                logger.error("❌ 资产29不存在")
                return
            
            logger.info(f"📊 资产29状态信息:")
            logger.info(f"   ID: {asset.id}")
            logger.info(f"   名称: {asset.name}")
            logger.info(f"   状态: {asset.status}")
            logger.info(f"   网络: {asset.network}")
            logger.info(f"   代币地址: {asset.token_address}")
            logger.info(f"   创建时间: {asset.created_at}")
            logger.info(f"   更新时间: {asset.updated_at}")
            
            # 查询上链历史
            histories = OnchainHistory.query.filter_by(asset_id=29).order_by(OnchainHistory.created_at.desc()).limit(5).all()
            
            logger.info(f"\n📈 最近5条上链历史:")
            for i, history in enumerate(histories, 1):
                logger.info(f"   {i}. 时间: {history.created_at}")
                logger.info(f"      状态: {history.status}")
                logger.info(f"      交易哈希: {history.transaction_hash}")
                logger.info(f"      错误信息: {history.error_message}")
                logger.info(f"      触发类型: {history.trigger_type}")
                logger.info(f"      网络费用: {history.network_fee}")
                logger.info("")
            
            # 检查钱包余额
            from app.utils.solana_compat.keypair import Keypair
            from app.utils.solana_compat.connection import Connection
            
            # 获取配置
            private_key_hex = os.environ.get("SOLANA_PRIVATE_KEY")
            if private_key_hex:
                try:
                    # 创建钱包
                    private_key_bytes = bytes.fromhex(private_key_hex)
                    wallet = Keypair.from_secret_key(private_key_bytes)
                    
                    # 创建连接
                    connection = Connection(os.environ.get("SOLANA_NETWORK_URL", "https://api.mainnet-beta.solana.com"))
                    
                    # 查询余额
                    balance = connection.get_balance(wallet.public_key)
                    logger.info(f"💰 钱包余额: {balance} lamports ({balance / 1e9:.9f} SOL)")
                    
                    # 计算费用
                    mint_rent = 570720  # Mint账户租金豁免
                    tx_fee = 15000      # 交易费用
                    total_cost = mint_rent + tx_fee
                    
                    logger.info(f"💸 预估费用: {total_cost} lamports ({total_cost / 1e9:.9f} SOL)")
                    
                    if balance >= total_cost:
                        logger.info("✅ 余额充足，可以进行上链操作")
                    else:
                        logger.warning(f"⚠️ 余额不足，还需要 {total_cost - balance} lamports")
                        
                except Exception as e:
                    logger.error(f"❌ 检查钱包余额时出错: {str(e)}")
            else:
                logger.warning("⚠️ 未配置SOLANA_PRIVATE_KEY")
                
        except Exception as e:
            logger.error(f"❌ 检查资产29状态时出错: {str(e)}")

if __name__ == "__main__":
    check_asset_29_status() 