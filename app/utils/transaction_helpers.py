import logging
from app.models import Transaction, TransactionType, TransactionStatus
from app.extensions import db
from datetime import datetime
import json

logger = logging.getLogger(__name__)

def record_fee_transaction(user_id, amount, blockchain, token_name=None, notes=None, tx_hash=None):
    """
    记录费用交易
    
    Args:
        user_id: 用户ID
        amount: 费用金额
        blockchain: 区块链名称 (例如 'solana', 'ethereum')
        token_name: 代币名称 (例如 'SOL', 'ETH', 'USDC')
        notes: 备注信息
        tx_hash: 交易哈希 (可选)
        
    Returns:
        Transaction: 创建的交易记录
    """
    try:
        # 创建交易记录
        transaction = Transaction(
            tx_hash=tx_hash or f"fee_{user_id}_{datetime.utcnow().timestamp()}",
            tx_type=TransactionType.FEE.value,
            status=TransactionStatus.CONFIRMED.value if tx_hash else TransactionStatus.PENDING.value,
            blockchain=blockchain,
            amount=amount,
            token_name=token_name,
            user_id=user_id,
            notes=notes or f"{blockchain} 交易费用",
            fee=amount  # 在费用交易中，金额就是费用
        )
        
        # 如果有交易哈希，设置确认时间
        if tx_hash:
            transaction.confirmed_at = datetime.utcnow()
        
        # 保存到数据库
        db.session.add(transaction)
        db.session.commit()
        
        logger.info(f"成功记录费用交易: 用户ID={user_id}, 金额={amount}, 区块链={blockchain}")
        return transaction
    
    except Exception as e:
        logger.error(f"记录费用交易失败: {str(e)}")
        db.session.rollback()
        return None

def record_blockchain_transaction(tx_type, user_id, amount, blockchain, token_address=None, token_name=None, 
                                  from_address=None, to_address=None, asset_id=None, 
                                  tx_hash=None, status=None, details=None):
    """
    记录区块链交易
    
    Args:
        tx_type: 交易类型 (TransactionType枚举值)
        user_id: 用户ID
        amount: 交易金额
        blockchain: 区块链名称
        token_address: 代币地址 (可选)
        token_name: 代币名称 (可选)
        from_address: 发送方地址 (可选)
        to_address: 接收方地址 (可选)
        asset_id: 资产ID (可选)
        tx_hash: 交易哈希 (可选)
        status: 交易状态 (可选，默认为PENDING)
        details: 交易详情 (可选，字典格式)
        
    Returns:
        Transaction: 创建的交易记录
    """
    try:
        # 创建交易记录
        transaction = Transaction(
            tx_hash=tx_hash or f"{tx_type}_{user_id}_{datetime.utcnow().timestamp()}",
            tx_type=tx_type,
            status=status or TransactionStatus.PENDING.value,
            blockchain=blockchain,
            amount=amount,
            token_address=token_address,
            token_name=token_name,
            from_address=from_address,
            to_address=to_address,
            user_id=user_id,
            asset_id=asset_id,
            details=json.dumps(details) if details else None
        )
        
        # 如果状态是已确认，设置确认时间
        if status == TransactionStatus.CONFIRMED.value:
            transaction.confirmed_at = datetime.utcnow()
        
        # 保存到数据库
        db.session.add(transaction)
        db.session.commit()
        
        logger.info(f"成功记录区块链交易: 类型={tx_type}, 用户ID={user_id}, 金额={amount}")
        return transaction
    
    except Exception as e:
        logger.error(f"记录区块链交易失败: {str(e)}")
        db.session.rollback()
        return None 