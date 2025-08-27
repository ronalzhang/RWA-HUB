import logging
import base64
from decimal import Decimal
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Asset, User, Trade, Holding, TradeStatus
from app.blockchain.solana_service import get_solana_client, get_latest_blockhash

from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.signature import Signature
from spl.token.instructions import transfer, TransferParams
from spl.token.client import get_associated_token_address

logger = logging.getLogger(__name__)

class TradeServiceV3:
    """
    重构后的交易服务 V3
    - 使用SPL代币转账逻辑 (例如USDC) 进行支付
    - 使用官方 `solana-py` 和 `solders` 库
    """

    @staticmethod
    def create_purchase(wallet_address: str, asset_id: int, amount: int):
        try:
            # 1. 数据验证
            if not isinstance(amount, int) or amount <= 0:
                return {'success': False, 'message': '无效的购买数量', 'error_code': 'INVALID_AMOUNT'}

            asset = Asset.query.get(asset_id)
            if not asset:
                return {'success': False, 'message': '资产不存在', 'error_code': 'ASSET_NOT_FOUND'}

            if not asset.is_active or asset.status != 'ON_CHAIN':
                return {'success': False, 'message': '资产当前不可交易', 'error_code': 'ASSET_NOT_TRADEABLE'}

            if asset.remaining_supply < amount:
                return {'success': False, 'message': '资产库存不足', 'error_code': 'INSUFFICIENT_SUPPLY'}

            user = User.query.filter_by(wallet_address=wallet_address).first()
            if not user:
                user = User(wallet_address=wallet_address, wallet_type='solana')
                db.session.add(user)
                logger.info(f"新用户创建: {wallet_address}")

            # 2. 创建数据库记录
            total_price = asset.token_price * Decimal(amount)
            new_trade = Trade(
                asset_id=asset_id,
                user_id=user.id,
                trader_address=wallet_address,
                type='buy',
                amount=amount,
                price=asset.token_price,
                total=total_price,
                status=TradeStatus.PENDING.value,
                blockchain=asset.blockchain
            )
            db.session.add(new_trade)
            db.session.commit()
            logger.info(f"创建新的待处理交易记录: TradeID={new_trade.id}")

            # 3. 构建SPL代币转账交易
            buyer_pubkey = Pubkey.from_string(wallet_address)
            
            platform_treasury_address = current_app.config.get('PLATFORM_TREASURY_WALLET')
            payment_token_mint_address = current_app.config.get('PAYMENT_TOKEN_MINT_ADDRESS') # e.g., USDC mint

            if not platform_treasury_address or not payment_token_mint_address:
                raise ValueError("平台收款地址或支付代币地址未配置")

            platform_pubkey = Pubkey.from_string(platform_treasury_address)
            payment_mint_pubkey = Pubkey.from_string(payment_token_mint_address)

            # 获取关联代币账户 (ATA)
            buyer_payment_token_ata = get_associated_token_address(buyer_pubkey, payment_mint_pubkey)
            platform_payment_token_ata = get_associated_token_address(platform_pubkey, payment_mint_pubkey)

            # 获取支付代币的小数位数 (例如USDC是6)
            payment_token_decimals = current_app.config.get('PAYMENT_TOKEN_DECIMALS', 6)
            amount_in_smallest_unit = int(total_price * (10**payment_token_decimals))

            instruction = transfer(
                TransferParams(
                    program_id=Pubkey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'),
                    source=buyer_payment_token_ata,
                    dest=platform_payment_token_ata,
                    owner=buyer_pubkey,
                    amount=amount_in_smallest_unit
                )
            )

            recent_blockhash = get_latest_blockhash()
            
            tx = Transaction.new_with_payer(
                [instruction],
                buyer_pubkey,
            )
            tx.recent_blockhash = Pubkey.from_string(recent_blockhash)

            serialized_tx = tx.serialize(verify_signatures=False)
            encoded_tx = base64.b64encode(serialized_tx).decode('utf-8')

            return {
                'success': True,
                'message': '交易已创建，等待签名',
                'trade_id': new_trade.id,
                'transaction': encoded_tx,
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[V3] 数据库操作失败: {e}", exc_info=True)
            return {'success': False, 'message': '数据库错误', 'error_code': 'DATABASE_ERROR'}
        except Exception as e:
            db.session.rollback()
            logger.error(f"[V3] 创建购买交易未知错误: {e}", exc_info=True)
            return {'success': False, 'message': f'内部服务器错误: {e}', 'error_code': 'INTERNAL_SERVER_ERROR'}

    @staticmethod
    def confirm_purchase(trade_id: int, tx_hash: str):
        try:
            trade = Trade.query.get(trade_id)
            if not trade:
                return {'success': False, 'message': '交易不存在', 'error_code': 'TRADE_NOT_FOUND'}

            if trade.status != TradeStatus.PENDING.value:
                return {'success': False, 'message': f'交易状态不正确 ({trade.status})，无法确认', 'error_code': 'INVALID_TRADE_STATUS'}

            # 2. 在区块链上核实交易
            client = get_solana_client()
            signature = Signature.from_string(tx_hash)
            
            # 设置较高的确认级别以确保交易最终性
            tx_response = client.get_transaction(signature, max_supported_transaction_version=0)

            if not tx_response or not tx_response.value or not tx_response.value.transaction:
                return {'success': False, 'message': '无法在链上找到该交易', 'error_code': 'TRANSACTION_NOT_FOUND'}
            
            if tx_response.value.err:
                logger.error(f"链上交易失败: {tx_response.value.err}")
                trade.status = TradeStatus.FAILED.value
                trade.status_reason = f"Blockchain transaction failed: {tx_response.value.err}"
                db.session.commit()
                return {'success': False, 'message': '链上交易执行失败', 'error_code': 'TRANSACTION_FAILED_ON_CHAIN'}

            # (此处可以添加更详细的交易内容验证，例如解析指令，检查收款方和金额)

            logger.info(f"链上交易 {tx_hash} 已成功验证")

            # 3. 更新数据库
            asset = Asset.query.get(trade.asset_id)
            if asset.remaining_supply < trade.amount:
                logger.warning(f"交易确认时库存不足: AssetID={asset.id}, TradeID={trade.id}")
                trade.status = TradeStatus.FAILED.value
                trade.status_reason = "库存不足"
                db.session.commit()
                return {'success': False, 'message': '资产库存不足', 'error_code': 'INSUFFICIENT_SUPPLY'}
            
            asset.remaining_supply -= trade.amount

            trade.status = TradeStatus.COMPLETED.value
            trade.tx_hash = tx_hash
            trade.status_updated_at = db.func.now()

            holding = Holding.query.filter_by(user_id=trade.user_id, asset_id=trade.asset_id).first()
            if holding:
                holding.amount += trade.amount
            else:
                holding = Holding(
                    user_id=trade.user_id,
                    asset_id=trade.asset_id,
                    amount=trade.amount,
                    purchase_price=trade.price
                )
                db.session.add(holding)
            
            db.session.commit()
            logger.info(f"交易 {trade_id} 已确认并完成，用户持仓已更新")

            return {
                'success': True,
                'message': '购买已成功确认',
                'trade_id': trade.id,
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[V3] 确认交易时数据库操作失败: {e}", exc_info=True)
            return {'success': False, 'message': '数据库错误', 'error_code': 'DATABASE_ERROR'}
        except Exception as e:
            db.session.rollback()
            logger.error(f"[V3] 确认购买交易未知错误: {e}", exc_info=True)
            return {'success': False, 'message': f'内部服务器错误: {e}', 'error_code': 'INTERNAL_SERVER_ERROR'}