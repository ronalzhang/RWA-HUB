"""
服务层 - 处理所有与资产交易相关的业务逻辑
"""
import logging
from decimal import Decimal
from datetime import datetime
from flask import current_app
from sqlalchemy.orm import sessionmaker
from app.extensions import db
from app.models import Asset, User, Trade, Holding
from app.models.asset import AssetStatus
from app.models.trade import TradeStatus, TradeType
from app.models.holding import HoldingStatus
# from app.services.commission_service import CommissionService
from app.blockchain.solana_service import SolanaService
from app.utils.error_handler import AppError

logger = logging.getLogger(__name__)

class TradeService:
    """
    封装所有与交易相关的业务逻辑，提供统一的服务入口。
    """

    def __init__(self, session=None):
        self.session = session or db.session
        self.solana_service = SolanaService()

    def create_purchase(self, user_address: str, asset_id: int, amount: int) -> dict:
        """
        创建一笔新的购买交易。这是购买流程的第一步。
        该方法负责验证、创建数据库记录，并返回需要前端签名的交易信息。

        Args:
            user_address (str): 购买者的钱包地址.
            asset_id (int): 所购买资产的ID.
            amount (int): 购买的数量.

        Returns:
            dict: 包含成功状态、交易ID和需要前端处理的区块链交易信息。
        
        Raises:
            AppError: 如果验证失败或发生任何业务逻辑错误。
        """
        logger.info(f"开始创建购买交易: 用户={user_address}, 资产ID={asset_id}, 数量={amount}")

        # 1. 验证输入
        if not user_address or not asset_id or not isinstance(amount, int) or amount <= 0:
            raise AppError("INVALID_INPUT", "无效的输入参数。")

        # 2. 查找用户，如果不存在则创建
        user = User.query.filter(
            (User.eth_address == user_address) | (User.solana_address == user_address)
        ).first()
        if not user:
            wallet_type = 'solana' if len(user_address) < 50 else 'ethereum'
            user = User(
                username=f"user_{user_address[:6]}", 
                email=f"{user_address}@auto.rwa", 
                wallet_type=wallet_type
            )
            # 根据钱包类型设置相应的地址字段
            if wallet_type == 'solana':
                user.solana_address = user_address
            else:
                user.eth_address = user_address
                
            self.session.add(user)
            self.session.flush()  # 为了获取 user.id
            logger.info(f"为地址 {user_address} 创建了新用户: ID={user.id}")

        # 3. 验证资产
        asset = self.session.query(Asset).filter_by(id=asset_id).with_for_update().first()
        if not asset:
            raise AppError("ASSET_NOT_FOUND", f"资产 {asset_id} 不存在。")
        if asset.status != AssetStatus.ON_CHAIN.value:
            raise AppError("ASSET_NOT_AVAILABLE", "该资产当前不可交易。")
        
        # 4. 检查库存
        # 使用 sold_supply 字段来计算剩余量
        remaining_supply = asset.token_supply - (asset.sold_supply or 0)
        if amount > remaining_supply:
            raise AppError("INSUFFICIENT_SUPPLY", f"资产库存不足，剩余: {remaining_supply}")

        # 5. 计算总价
        total_price = Decimal(str(asset.token_price)) * Decimal(amount)

        # 6. 创建并保存交易记录
        try:
            new_trade = Trade(
                asset_id=asset.id,
                trader_address=user_address,
                type=TradeType.BUY.value,
                amount=amount,
                price=Decimal(str(asset.token_price)),
                total=total_price,
                status=TradeStatus.PENDING.value,
                created_at=datetime.utcnow()
            )
            self.session.add(new_trade)
            self.session.flush() # 为了获取 new_trade.id
            logger.info(f"已创建待处理的交易记录: ID={new_trade.id}")

            # 7. 构建待签名的区块链交易 (这里仅为示例，具体实现依赖区块链服务)
            # 实际应调用solana_service来构建一个待签名的交易对象
            transaction_to_sign = self.solana_service.build_purchase_transaction(
                buyer_address=user_address,
                seller_address=asset.owner_address,
                token_mint_address=asset.token_address,
                amount=amount,
                total_price=total_price
            )

            self.session.commit()
            logger.info(f"交易 {new_trade.id} 创建成功，等待前端签名。")

            return {
                "success": True,
                "message": "交易创建成功，等待签名。",
                "trade_id": new_trade.id,
                "transaction_to_sign": transaction_to_sign # 前端需要签名的交易数据
            }

        except Exception as e:
            self.session.rollback()
            logger.error(f"创建交易记录时出错: {e}", exc_info=True)
            raise AppError("DATABASE_ERROR", "创建交易失败，请重试。")

    def confirm_purchase(self, trade_id: int, tx_hash: str) -> dict:
        """
        确认购买交易。这是购买流程的第二步。
        该方法在前端返回交易签名后被调用，用以验证交易并更新系统状态。

        Args:
            trade_id (int): 待确认的交易ID.
            tx_hash (str): 区块链返回的交易哈希/签名.

        Returns:
            dict: 包含成功状态和最终交易信息的字典。
        
        Raises:
            AppError: 如果交易未找到、状态不正确或确认过程中发生错误。
        """
        logger.info(f"开始确认购买交易: 交易ID={trade_id}, 交易哈希={tx_hash}")

        # 1. 验证输入
        if not trade_id or not tx_hash:
            raise AppError("INVALID_INPUT", "交易ID和交易哈希不能为空。")

        # 2. 查找交易记录
        trade = self.session.query(Trade).filter_by(id=trade_id).with_for_update().first()
        if not trade:
            raise AppError("TRADE_NOT_FOUND", f"交易 {trade_id} 不存在。")
        if trade.status != TradeStatus.PENDING.value:
            raise AppError("TRADE_NOT_PENDING", f"交易 {trade_id} 状态不正确，无法确认。")

        # 3. (模拟) 验证链上交易状态
        # 在真实应用中，这里需要轮询Solana网络，确认tx_hash是否成功
        is_tx_successful = self.solana_service.verify_transaction(tx_hash)
        if not is_tx_successful:
            # 如果交易失败，更新状态并返回
            trade.status = TradeStatus.FAILED.value
            trade.tx_hash = tx_hash
            self.session.commit()
            logger.warning(f"交易 {trade_id} 在链上验证失败。")
            raise AppError("BLOCKCHAIN_TX_FAILED", "区块链交易失败或未找到。")

        # 4. 更新交易状态
        try:
            trade.status = TradeStatus.COMPLETED.value
            trade.tx_hash = tx_hash
            trade.updated_at = datetime.utcnow()
            logger.info(f"交易 {trade_id} 状态更新为 COMPLETED。")

            # 5. 更新资产已售出数量
            asset = self.session.query(Asset).filter_by(id=trade.asset_id).with_for_update().first()
            if not asset:
                 raise AppError("ASSET_NOT_FOUND", f"交易关联的资产 {trade.asset_id} 不存在。")
            
            asset.sold_supply = (asset.sold_supply or 0) + trade.amount
            logger.info(f"资产 {asset.id} 已售出数量更新为: {asset.sold_supply}")

            # 6. 更新或创建用户持仓 (Holding)
            self.update_user_holding(trade.trader_address, trade.asset_id, trade.amount)

            # 7. 计算并记录佣金
            # commission_service = CommissionService(self.session)
            # commission_service.process_commission_for_trade(trade)

            self.session.commit()
            logger.info(f"交易 {trade_id} 已成功确认并完成所有系统更新。")

            return {
                "success": True,
                "message": "购买已成功确认！",
                "trade": trade.to_dict()
            }

        except Exception as e:
            self.session.rollback()
            logger.error(f"确认交易 {trade_id} 时发生内部错误: {e}", exc_info=True)
            raise AppError("INTERNAL_ERROR", "确认交易时发生未知错误。")

    def update_user_holding(self, user_address: str, asset_id: int, amount_change: int):
        """
        更新用户的资产持有量。

        Args:
            user_address (str): 用户钱包地址.
            asset_id (int): 资产ID.
            amount_change (int): 变化的数量 (正数为增加，负数为减少).
        """
        user = User.query.filter(
            (User.eth_address == user_address) | (User.solana_address == user_address)
        ).first()
        if not user:
            logger.warning(f"更新持仓失败：找不到用户 {user_address}")
            return

        holding = self.session.query(Holding).filter_by(
            user_id=user.id, 
            asset_id=asset_id
        ).with_for_update().first()

        if holding:
            holding.quantity += amount_change
            holding.updated_at = datetime.utcnow()
            logger.info(f"更新用户 {user.id} 对资产 {asset_id} 的持仓，新数量: {holding.quantity}")
        else:
            holding = Holding(
                user_id=user.id,
                asset_id=asset_id,
                quantity=amount_change,
                status=HoldingStatus.ACTIVE.value,
                created_at=datetime.utcnow()
            )
            self.session.add(holding)
            logger.info(f"为用户 {user.id} 创建新的资产 {asset_id} 持仓记录，数量: {amount_change}")

        if holding.quantity <= 0:
            self.session.delete(holding)
            logger.info(f"用户 {user.id} 对资产 {asset_id} 的持仓已清空，删除记录。")
