import logging
import base64
import time
from decimal import Decimal
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Asset, User, Trade, Holding, TradeStatus
from app.blockchain.solana_service import get_solana_client, get_latest_blockhash_with_cache, validate_solana_address
from app.services.transaction_monitor import transaction_monitor, TransactionStatus
from app.services.log_aggregator import transaction_log_aggregator

from solders.pubkey import Pubkey
from solders.hash import Hash
from solders.signature import Signature
from solders.transaction import Transaction
from spl.token.instructions import transfer, TransferParams, get_associated_token_address
from solana.exceptions import SolanaRpcException
from solana.rpc.types import TxOpts

logger = logging.getLogger(__name__)

class TradeServiceV3:
    """
    重构后的交易服务 V3
    - 使用SPL代币转账逻辑 (例如USDC) 进行支付
    - 使用官方 `solana-py` 和 `solders` 库
    - 包含全面的错误处理和日志记录
    """

    # 错误代码常量
    class ErrorCodes:
        INVALID_AMOUNT = 'INVALID_AMOUNT'
        ASSET_NOT_FOUND = 'ASSET_NOT_FOUND'
        ASSET_NOT_TRADEABLE = 'ASSET_NOT_TRADEABLE'
        INSUFFICIENT_SUPPLY = 'INSUFFICIENT_SUPPLY'
        CONFIGURATION_ERROR = 'CONFIGURATION_ERROR'
        BLOCKCHAIN_CONNECTION_ERROR = 'BLOCKCHAIN_CONNECTION_ERROR'
        BLOCKHASH_RETRIEVAL_ERROR = 'BLOCKHASH_RETRIEVAL_ERROR'
        INSTRUCTION_CREATION_ERROR = 'INSTRUCTION_CREATION_ERROR'
        TRANSACTION_BUILD_ERROR = 'TRANSACTION_BUILD_ERROR'
        TRANSACTION_SERIALIZATION_ERROR = 'TRANSACTION_SERIALIZATION_ERROR'
        TRANSACTION_VALIDATION_ERROR = 'TRANSACTION_VALIDATION_ERROR'
        DATABASE_ERROR = 'DATABASE_ERROR'
        INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR'
        TRADE_NOT_FOUND = 'TRADE_NOT_FOUND'
        INVALID_TRADE_STATUS = 'INVALID_TRADE_STATUS'
        TRANSACTION_NOT_FOUND = 'TRANSACTION_NOT_FOUND'
        TRANSACTION_FAILED_ON_CHAIN = 'TRANSACTION_FAILED_ON_CHAIN'

    @staticmethod
    def create_purchase(wallet_address: str, asset_id: int, amount: int):
        """
        创建购买交易，包含全面的错误处理和日志记录
        
        Args:
            wallet_address: 买方钱包地址
            asset_id: 资产ID
            amount: 购买数量
            
        Returns:
            dict: 包含成功状态、消息、交易ID和序列化交易的字典
        """
        transaction_id = f"tx_{int(time.time() * 1000)}"  # 用于关联日志的交易ID
        start_time = time.time()
        logger.info(f"[{transaction_id}] 开始创建购买交易: 钱包={wallet_address}, 资产ID={asset_id}, 数量={amount}")
        
        # Record blockchain connection attempt
        try:
            get_solana_client()
            transaction_monitor.record_blockchain_connection(True)
        except Exception as e:
            transaction_monitor.record_blockchain_connection(False, error_message=str(e))
        
        try:
            # 1. 数据验证阶段
            logger.debug(f"[{transaction_id}] 步骤1: 开始数据验证")
            
            try:
                if not isinstance(amount, int) or amount <= 0:
                    logger.warning(f"[{transaction_id}] 数据验证失败: 无效的购买数量 {amount}")
                    return TradeServiceV3._create_error_response(
                        TradeServiceV3.ErrorCodes.INVALID_AMOUNT, 
                        '无效的购买数量'
                    )

                asset = Asset.query.get(asset_id)
                TradeServiceV3._log_database_operation(transaction_id, "QUERY_ASSET", {
                    "asset_id": asset_id,
                    "found": asset is not None
                })
                if not asset:
                    logger.warning(f"[{transaction_id}] 数据验证失败: 资产不存在 {asset_id}")
                    return TradeServiceV3._create_error_response(
                        TradeServiceV3.ErrorCodes.ASSET_NOT_FOUND, 
                        '资产不存在'
                    )

                # 检查资产状态是否为活跃状态（ACTIVE=2, ON_CHAIN=2, APPROVED=2）
                if asset.status != 2:  # AssetStatus.ACTIVE.value = 2
                    logger.warning(f"[{transaction_id}] 数据验证失败: 资产不可交易 {asset_id}, 状态={asset.status}")
                    return TradeServiceV3._create_error_response(
                        TradeServiceV3.ErrorCodes.ASSET_NOT_TRADEABLE, 
                        '资产当前不可交易'
                    )

                if asset.remaining_supply < amount:
                    logger.warning(f"[{transaction_id}] 数据验证失败: 库存不足 {asset.remaining_supply} < {amount}")
                    return TradeServiceV3._create_error_response(
                        TradeServiceV3.ErrorCodes.INSUFFICIENT_SUPPLY, 
                        '资产库存不足'
                    )

                logger.debug(f"[{transaction_id}] 数据验证通过")
                
            except Exception as e:
                logger.error(f"[{transaction_id}] 数据验证阶段发生异常: {e}", exc_info=True)
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.INTERNAL_SERVER_ERROR, 
                    f'数据验证失败: {str(e)}'
                )

            # 2. 用户处理和数据库记录创建阶段
            logger.debug(f"[{transaction_id}] 步骤2: 开始用户处理和数据库记录创建")
            
            try:
                logger.debug(f"[{transaction_id}] 数据库事务开始: 查询用户和创建交易记录")
                
                user = User.query.filter_by(solana_address=wallet_address).first()
                TradeServiceV3._log_database_operation(transaction_id, "QUERY_USER", {
                    "wallet_address": wallet_address,
                    "found": user is not None
                })
                if not user:
                    logger.debug(f"[{transaction_id}] 用户不存在，创建新用户: {wallet_address}")
                    user = User(wallet_address=wallet_address, wallet_type='solana')
                    db.session.add(user)
                    TradeServiceV3._log_database_operation(transaction_id, "CREATE_USER", {
                        "wallet_address": wallet_address,
                        "wallet_type": "solana"
                    })
                    logger.info(f"[{transaction_id}] 新用户已添加到会话: {wallet_address}")
                else:
                    logger.debug(f"[{transaction_id}] 找到现有用户: ID={user.id}, 钱包={wallet_address}")
                    TradeServiceV3._log_database_operation(transaction_id, "FOUND_USER", {
                        "user_id": user.id,
                        "wallet_address": wallet_address
                    })

                total_price = asset.token_price * Decimal(amount)
                logger.debug(f"[{transaction_id}] 计算交易总价: {asset.token_price} × {amount} = {total_price}")
                
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
                TradeServiceV3._log_database_operation(transaction_id, "CREATE_TRADE", {
                    "asset_id": asset_id,
                    "user_id": user.id,
                    "amount": amount,
                    "price": asset.token_price,
                    "total": total_price,
                    "status": TradeStatus.PENDING.value,
                    "blockchain": asset.blockchain
                })
                logger.debug(f"[{transaction_id}] 交易记录已添加到会话: 资产ID={asset_id}, 数量={amount}, 状态={TradeStatus.PENDING.value}")
                
                # 提交事务前记录
                logger.debug(f"[{transaction_id}] 准备提交数据库事务: 用户创建/更新 + 交易记录创建")
                db.session.commit()
                logger.info(f"[{transaction_id}] 数据库事务提交成功: TradeID={new_trade.id}, UserID={user.id}, 总价={total_price}")
                
            except SQLAlchemyError as e:
                logger.error(f"[{transaction_id}] 数据库SQLAlchemy错误，执行回滚: {e}", exc_info=True)
                db.session.rollback()
                logger.debug(f"[{transaction_id}] 数据库事务已回滚")
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.DATABASE_ERROR, 
                    '数据库操作失败'
                )

            # 3. 配置验证阶段
            logger.debug(f"[{transaction_id}] 步骤3: 开始配置验证")
            
            try:
                config_result = TradeServiceV3._validate_configuration()
                if not config_result['valid']:
                    logger.error(f"[{transaction_id}] 配置验证失败: {config_result['message']}")
                    return TradeServiceV3._create_error_response(
                        TradeServiceV3.ErrorCodes.CONFIGURATION_ERROR, 
                        config_result['message']
                    )
                
                platform_treasury_address = config_result['config']['PLATFORM_TREASURY_WALLET']
                payment_token_mint_address = config_result['config']['PAYMENT_TOKEN_MINT_ADDRESS']
                payment_token_decimals = config_result['config']['PAYMENT_TOKEN_DECIMALS']
                
                logger.debug(f"[{transaction_id}] 配置验证通过")
                
            except Exception as e:
                logger.error(f"[{transaction_id}] 配置验证阶段发生异常: {e}", exc_info=True)
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.CONFIGURATION_ERROR, 
                    f'配置验证失败: {str(e)}'
                )

            # 4. 区块哈希检索阶段
            logger.debug(f"[{transaction_id}] 步骤4: 开始区块哈希检索")
            
            try:
                recent_blockhash = get_latest_blockhash_with_cache()
                logger.debug(f"[{transaction_id}] 区块哈希检索成功: {str(recent_blockhash)[:8]}...")
                
            except Exception as e:
                logger.error(f"[{transaction_id}] 区块哈希检索失败: {e}", exc_info=True)
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.BLOCKHASH_RETRIEVAL_ERROR, 
                    f'无法获取区块哈希: {str(e)}'
                )

            # 5. 指令创建阶段
            logger.debug(f"[{transaction_id}] 步骤5: 开始指令创建")
            
            try:
                instruction = TradeServiceV3._create_transfer_instruction(
                    wallet_address, 
                    platform_treasury_address, 
                    payment_token_mint_address, 
                    total_price, 
                    payment_token_decimals,
                    transaction_id
                )
                logger.debug(f"[{transaction_id}] 指令创建成功")
                
            except Exception as e:
                logger.error(f"[{transaction_id}] 指令创建失败: {e}", exc_info=True)
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.INSTRUCTION_CREATION_ERROR, 
                    f'指令创建失败: {str(e)}'
                )

            # 6. 交易构建阶段
            logger.debug(f"[{transaction_id}] 步骤6: 开始交易构建")
            
            try:
                from solana.publickey import PublicKey
                
                buyer_pubkey = PublicKey(wallet_address)
                tx = Transaction()
                tx.add(instruction)
                tx.recent_blockhash = recent_blockhash
                tx.fee_payer = buyer_pubkey
                
                logger.debug(f"[{transaction_id}] 交易构建成功: 指令数={len(tx.instructions)}")
                
            except Exception as e:
                logger.error(f"[{transaction_id}] 交易构建失败: {e}", exc_info=True)
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.TRANSACTION_BUILD_ERROR, 
                    f'交易构建失败: {str(e)}'
                )

            # 7. 交易验证阶段
            logger.debug(f"[{transaction_id}] 步骤7: 开始交易验证")
            
            try:
                if not TradeServiceV3._validate_transaction(tx, transaction_id):
                    logger.error(f"[{transaction_id}] 交易验证失败")
                    return TradeServiceV3._create_error_response(
                        TradeServiceV3.ErrorCodes.TRANSACTION_VALIDATION_ERROR, 
                        '交易验证失败'
                    )
                logger.debug(f"[{transaction_id}] 交易验证通过")
                
            except Exception as e:
                logger.error(f"[{transaction_id}] 交易验证阶段发生异常: {e}", exc_info=True)
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.TRANSACTION_VALIDATION_ERROR, 
                    f'交易验证失败: {str(e)}'
                )

            # 8. 交易序列化阶段
            logger.debug(f"[{transaction_id}] 步骤8: 开始交易序列化")
            
            try:
                serialized_tx = tx.serialize()
                encoded_tx = base64.b64encode(serialized_tx).decode('utf-8')
                
                logger.info(f"[{transaction_id}] 交易序列化成功: 长度={len(serialized_tx)}, Base64长度={len(encoded_tx)}")
                logger.debug(f"[{transaction_id}] 序列化交易前8字节: {serialized_tx[:8].hex()}")
                
            except Exception as e:
                logger.error(f"[{transaction_id}] 交易序列化失败: {e}", exc_info=True)
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.TRANSACTION_SERIALIZATION_ERROR, 
                    f'交易序列化失败: {str(e)}'
                )

            # 成功完成
            duration_ms = int((time.time() - start_time) * 1000)
            amount_in_smallest_unit = int(total_price * (10**payment_token_decimals))
            logger.info(f"[{transaction_id}] 交易创建完全成功: TradeID={new_trade.id}, 买方={wallet_address}, USDC金额={amount_in_smallest_unit}")
            
            # Record successful transaction creation
            transaction_monitor.record_transaction_attempt(
                TransactionStatus.SUCCESS,
                trade_id=new_trade.id,
                duration_ms=duration_ms
            )
            
            # Log successful transaction creation
            transaction_log_aggregator.process_log_entry(
                'INFO',
                f"Transaction creation successful: TradeID={new_trade.id}",
                'TradeServiceV3',
                {
                    'trade_id': new_trade.id,
                    'wallet_address': wallet_address,
                    'asset_id': asset_id,
                    'amount': amount,
                    'duration_ms': duration_ms
                }
            )
            
            return {
                'success': True,
                'message': '交易已创建，等待签名',
                'trade_id': new_trade.id,
                'transaction': encoded_tx,
                'transaction_id': transaction_id
            }

        except SQLAlchemyError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{transaction_id}] 顶层数据库SQLAlchemy错误，执行回滚: {e}", exc_info=True)
            db.session.rollback()
            logger.debug(f"[{transaction_id}] 顶层数据库事务已回滚")
            
            # Record failed transaction creation
            transaction_monitor.record_transaction_attempt(
                TransactionStatus.FAILED,
                error_type='database_error',
                error_message=str(e),
                duration_ms=duration_ms
            )
            
            # Log failed transaction creation
            transaction_log_aggregator.process_log_entry(
                'ERROR',
                f"Transaction creation failed: Database error - {str(e)}",
                'TradeServiceV3',
                {
                    'error_type': 'database_error',
                    'wallet_address': wallet_address,
                    'asset_id': asset_id,
                    'amount': amount,
                    'duration_ms': duration_ms
                }
            )
            
            return TradeServiceV3._create_error_response(
                TradeServiceV3.ErrorCodes.DATABASE_ERROR, 
                '数据库错误'
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{transaction_id}] 顶层未知错误，执行回滚: {e}", exc_info=True)
            db.session.rollback()
            logger.debug(f"[{transaction_id}] 顶层数据库事务已回滚")
            
            # Record failed transaction creation
            transaction_monitor.record_transaction_attempt(
                TransactionStatus.FAILED,
                error_type='internal_server_error',
                error_message=str(e),
                duration_ms=duration_ms
            )
            
            # Log failed transaction creation
            transaction_log_aggregator.process_log_entry(
                'ERROR',
                f"Transaction creation failed: Internal server error - {str(e)}",
                'TradeServiceV3',
                {
                    'error_type': 'internal_server_error',
                    'wallet_address': wallet_address,
                    'asset_id': asset_id,
                    'amount': amount,
                    'duration_ms': duration_ms
                }
            )
            
            return TradeServiceV3._create_error_response(
                TradeServiceV3.ErrorCodes.INTERNAL_SERVER_ERROR, 
                f'内部服务器错误: {str(e)}'
            )

    @staticmethod
    def confirm_purchase(trade_id: int, tx_hash: str):
        """
        确认购买交易，包含全面的错误处理和日志记录
        
        Args:
            trade_id: 交易ID
            tx_hash: 交易哈希
            
        Returns:
            dict: 包含成功状态和消息的字典
        """
        confirmation_id = f"confirm_{trade_id}_{int(time.time() * 1000)}"
        logger.info(f"[{confirmation_id}] 开始确认购买交易: TradeID={trade_id}, TxHash={tx_hash}")
        
        try:
            # 1. 交易记录验证阶段
            logger.debug(f"[{confirmation_id}] 步骤1: 开始交易记录验证")
            
            try:
                trade = Trade.query.get(trade_id)
                TradeServiceV3._log_database_operation(confirmation_id, "QUERY_TRADE", {
                    "trade_id": trade_id,
                    "found": trade is not None
                })
                if not trade:
                    logger.warning(f"[{confirmation_id}] 交易记录不存在: {trade_id}")
                    return TradeServiceV3._create_error_response(
                        TradeServiceV3.ErrorCodes.TRADE_NOT_FOUND, 
                        '交易不存在'
                    )

                if trade.status != TradeStatus.PENDING.value:
                    logger.warning(f"[{confirmation_id}] 交易状态不正确: {trade.status}, 期望: {TradeStatus.PENDING.value}")
                    return TradeServiceV3._create_error_response(
                        TradeServiceV3.ErrorCodes.INVALID_TRADE_STATUS, 
                        f'交易状态不正确 ({trade.status})，无法确认'
                    )
                
                logger.debug(f"[{confirmation_id}] 交易记录验证通过: 状态={trade.status}, 金额={trade.amount}")
                
            except Exception as e:
                logger.error(f"[{confirmation_id}] 交易记录验证阶段发生异常: {e}", exc_info=True)
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.INTERNAL_SERVER_ERROR, 
                    f'交易记录验证失败: {str(e)}'
                )

            # 2. 区块链交易验证阶段
            logger.debug(f"[{confirmation_id}] 步骤2: 开始区块链交易验证")
            
            try:
                blockchain_result = TradeServiceV3._verify_blockchain_transaction(tx_hash, confirmation_id)
                if not blockchain_result['valid']:
                    # 更新交易状态为失败
                    try:
                        logger.debug(f"[{confirmation_id}] 准备更新交易状态为失败: TradeID={trade.id}")
                        old_status = trade.status
                        trade.status = TradeStatus.FAILED.value
                        trade.status_reason = blockchain_result['message']
                        TradeServiceV3._log_database_operation(confirmation_id, "UPDATE_TRADE_TO_FAILED", {
                            "trade_id": trade.id,
                            "old_status": old_status,
                            "new_status": TradeStatus.FAILED.value,
                            "reason": blockchain_result['message']
                        })
                        logger.debug(f"[{confirmation_id}] 交易状态变更: {old_status} -> {TradeStatus.FAILED.value}, 原因: {blockchain_result['message']}")
                        db.session.commit()
                        logger.info(f"[{confirmation_id}] 交易状态已更新为失败: TradeID={trade.id}, 原因={blockchain_result['message']}")
                    except SQLAlchemyError as db_e:
                        logger.error(f"[{confirmation_id}] 更新交易失败状态时数据库错误: {db_e}", exc_info=True)
                        db.session.rollback()
                        logger.debug(f"[{confirmation_id}] 失败状态更新事务已回滚")
                    
                    return TradeServiceV3._create_error_response(
                        blockchain_result['error_code'], 
                        blockchain_result['message']
                    )
                
                logger.debug(f"[{confirmation_id}] 区块链交易验证通过")
                
            except Exception as e:
                logger.error(f"[{confirmation_id}] 区块链交易验证阶段发生异常: {e}", exc_info=True)
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.BLOCKCHAIN_CONNECTION_ERROR, 
                    f'区块链验证失败: {str(e)}'
                )

            # 3. 库存检查和数据库更新阶段
            logger.debug(f"[{confirmation_id}] 步骤3: 开始库存检查和数据库更新")
            
            try:
                asset = Asset.query.get(trade.asset_id)
                TradeServiceV3._log_database_operation(confirmation_id, "QUERY_ASSET_FOR_CONFIRMATION", {
                    "asset_id": trade.asset_id,
                    "trade_id": trade.id,
                    "found": asset is not None
                })
                if not asset:
                    logger.error(f"[{confirmation_id}] 资产不存在: {trade.asset_id}")
                    return TradeServiceV3._create_error_response(
                        TradeServiceV3.ErrorCodes.ASSET_NOT_FOUND, 
                        '关联资产不存在'
                    )
                
                if asset.remaining_supply < trade.amount:
                    logger.warning(f"[{confirmation_id}] 交易确认时库存不足: AssetID={asset.id}, 剩余={asset.remaining_supply}, 需要={trade.amount}")
                    logger.debug(f"[{confirmation_id}] 准备将交易标记为失败: 库存不足")
                    old_status = trade.status
                    trade.status = TradeStatus.FAILED.value
                    trade.status_reason = "库存不足"
                    TradeServiceV3._log_database_operation(confirmation_id, "UPDATE_TRADE_TO_FAILED", {
                        "trade_id": trade.id,
                        "old_status": old_status,
                        "new_status": TradeStatus.FAILED.value,
                        "reason": "库存不足",
                        "required_amount": trade.amount,
                        "available_supply": asset.remaining_supply
                    })
                    logger.debug(f"[{confirmation_id}] 交易状态变更: {old_status} -> {TradeStatus.FAILED.value}")
                    db.session.commit()
                    logger.info(f"[{confirmation_id}] 交易因库存不足已标记为失败: TradeID={trade.id}")
                    return TradeServiceV3._create_error_response(
                        TradeServiceV3.ErrorCodes.INSUFFICIENT_SUPPLY, 
                        '资产库存不足'
                    )
                
                # 记录更新前的状态
                old_asset_supply = asset.remaining_supply
                old_trade_status = trade.status
                
                logger.debug(f"[{confirmation_id}] 开始数据库更新事务: 资产库存={old_asset_supply}, 交易状态={old_trade_status}")
                
                # 更新资产库存
                asset.remaining_supply -= trade.amount
                TradeServiceV3._log_database_operation(confirmation_id, "UPDATE_ASSET_SUPPLY", {
                    "asset_id": asset.id,
                    "old_supply": old_asset_supply,
                    "new_supply": asset.remaining_supply,
                    "amount_sold": trade.amount
                })
                logger.debug(f"[{confirmation_id}] 资产库存更新: {old_asset_supply} -> {asset.remaining_supply} (减少 {trade.amount})")
                
                # 更新交易状态
                trade.status = TradeStatus.COMPLETED.value
                trade.tx_hash = tx_hash
                trade.status_updated_at = db.func.now()
                TradeServiceV3._log_database_operation(confirmation_id, "UPDATE_TRADE_STATUS", {
                    "trade_id": trade.id,
                    "old_status": old_trade_status,
                    "new_status": TradeStatus.COMPLETED.value,
                    "tx_hash": tx_hash
                })
                logger.debug(f"[{confirmation_id}] 交易状态更新: {old_trade_status} -> {TradeStatus.COMPLETED.value}, TxHash={tx_hash}")
                
                # 更新或创建用户持仓
                holding = Holding.query.filter_by(user_id=trade.user_id, asset_id=trade.asset_id).first()
                TradeServiceV3._log_database_operation(confirmation_id, "QUERY_HOLDING", {
                    "user_id": trade.user_id,
                    "asset_id": trade.asset_id,
                    "found": holding is not None
                })
                if holding:
                    old_amount = holding.amount
                    holding.amount += trade.amount
                    TradeServiceV3._log_database_operation(confirmation_id, "UPDATE_HOLDING", {
                        "user_id": trade.user_id,
                        "asset_id": trade.asset_id,
                        "old_amount": old_amount,
                        "new_amount": holding.amount,
                        "added_amount": trade.amount
                    })
                    logger.debug(f"[{confirmation_id}] 更新现有用户持仓: UserID={trade.user_id}, AssetID={trade.asset_id}, {old_amount} -> {holding.amount}")
                else:
                    holding = Holding(
                        user_id=trade.user_id,
                        asset_id=trade.asset_id,
                        amount=trade.amount,
                        purchase_price=trade.price
                    )
                    db.session.add(holding)
                    TradeServiceV3._log_database_operation(confirmation_id, "CREATE_HOLDING", {
                        "user_id": trade.user_id,
                        "asset_id": trade.asset_id,
                        "amount": trade.amount,
                        "purchase_price": trade.price
                    })
                    logger.debug(f"[{confirmation_id}] 创建新用户持仓: UserID={trade.user_id}, AssetID={trade.asset_id}, 数量={trade.amount}, 价格={trade.price}")
                
                # 提交前记录即将提交的更改
                logger.debug(f"[{confirmation_id}] 准备提交数据库事务: 资产库存更新 + 交易状态更新 + 用户持仓更新")
                db.session.commit()
                logger.info(f"[{confirmation_id}] 数据库事务提交成功: TradeID={trade.id} 已完成，资产库存={asset.remaining_supply}，用户持仓={holding.amount}")
                
            except SQLAlchemyError as e:
                logger.error(f"[{confirmation_id}] 数据库SQLAlchemy错误，执行回滚: {e}", exc_info=True)
                db.session.rollback()
                logger.debug(f"[{confirmation_id}] 数据库事务已回滚: 所有更改已撤销")
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.DATABASE_ERROR, 
                    '数据库更新失败'
                )
            except Exception as e:
                logger.error(f"[{confirmation_id}] 数据库更新阶段发生异常，执行回滚: {e}", exc_info=True)
                db.session.rollback()
                logger.debug(f"[{confirmation_id}] 数据库事务已回滚: 所有更改已撤销")
                return TradeServiceV3._create_error_response(
                    TradeServiceV3.ErrorCodes.INTERNAL_SERVER_ERROR, 
                    f'数据库更新失败: {str(e)}'
                )

            # 成功完成
            logger.info(f"[{confirmation_id}] 交易确认完全成功: TradeID={trade.id}, TxHash={tx_hash}")
            
            return {
                'success': True,
                'message': '购买已成功确认',
                'trade_id': trade.id,
                'confirmation_id': confirmation_id
            }

        except SQLAlchemyError as e:
            logger.error(f"[{confirmation_id}] 顶层数据库SQLAlchemy错误，执行回滚: {e}", exc_info=True)
            db.session.rollback()
            logger.debug(f"[{confirmation_id}] 顶层数据库事务已回滚")
            return TradeServiceV3._create_error_response(
                TradeServiceV3.ErrorCodes.DATABASE_ERROR, 
                '数据库错误'
            )
        except Exception as e:
            logger.error(f"[{confirmation_id}] 顶层未知错误，执行回滚: {e}", exc_info=True)
            db.session.rollback()
            logger.debug(f"[{confirmation_id}] 顶层数据库事务已回滚")
            return TradeServiceV3._create_error_response(
                TradeServiceV3.ErrorCodes.INTERNAL_SERVER_ERROR, 
                f'内部服务器错误: {str(e)}'
            )

    @staticmethod
    def _verify_blockchain_transaction(tx_hash: str, confirmation_id: str, max_retries: int = 3) -> dict:
        """
        验证区块链上的交易，包含重试机制
        
        Args:
            tx_hash: 交易哈希
            confirmation_id: 确认ID用于日志关联
            max_retries: 最大重试次数
            
        Returns:
            dict: 包含验证结果的字典
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"[{confirmation_id}] 区块链交易验证重试 {attempt}/{max_retries}")
                    time.sleep(1.0 * attempt)  # 指数退避
                
                client = get_solana_client()
                signature = Signature.from_string(tx_hash)
                
                # 设置较高的确认级别以确保交易最终性
                tx_response = client.get_transaction(signature, max_supported_transaction_version=0)

                if not tx_response or not tx_response.value or not tx_response.value.transaction:
                    if attempt < max_retries:
                        logger.warning(f"[{confirmation_id}] 链上交易未找到，将重试 (尝试 {attempt + 1}/{max_retries + 1})")
                        last_exception = Exception("无法在链上找到该交易")
                        continue
                    else:
                        return {
                            'valid': False,
                            'error_code': TradeServiceV3.ErrorCodes.TRANSACTION_NOT_FOUND,
                            'message': '无法在链上找到该交易'
                        }
                
                if tx_response.value.err:
                    error_msg = f"链上交易执行失败: {tx_response.value.err}"
                    logger.error(f"[{confirmation_id}] {error_msg}")
                    return {
                        'valid': False,
                        'error_code': TradeServiceV3.ErrorCodes.TRANSACTION_FAILED_ON_CHAIN,
                        'message': '链上交易执行失败'
                    }

                # 交易验证成功
                logger.info(f"[{confirmation_id}] 链上交易 {tx_hash} 验证成功")
                return {
                    'valid': True,
                    'message': '区块链交易验证通过',
                    'transaction_data': tx_response.value
                }
                
            except SolanaRpcException as e:
                last_exception = e
                logger.warning(f"[{confirmation_id}] 区块链RPC错误 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                if attempt == max_retries:
                    break
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"[{confirmation_id}] 区块链验证异常 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                if attempt == max_retries:
                    break
        
        # 所有重试都失败了
        logger.error(f"[{confirmation_id}] 区块链交易验证最终失败，已重试 {max_retries} 次")
        return {
            'valid': False,
            'error_code': TradeServiceV3.ErrorCodes.BLOCKCHAIN_CONNECTION_ERROR,
            'message': f'区块链连接失败，已重试 {max_retries} 次: {str(last_exception)}'
        }

    @staticmethod
    def _log_database_operation(operation_id: str, operation_type: str, details: dict = None):
        """
        记录数据库操作的详细信息
        
        Args:
            operation_id: 操作关联ID (transaction_id 或 confirmation_id)
            operation_type: 操作类型 (CREATE_USER, CREATE_TRADE, UPDATE_TRADE, etc.)
            details: 操作详情字典
        """
        try:
            log_msg = f"[{operation_id}] 数据库操作: {operation_type}"
            if details:
                detail_parts = []
                for key, value in details.items():
                    if isinstance(value, (int, float, str, bool)):
                        detail_parts.append(f"{key}={value}")
                    else:
                        detail_parts.append(f"{key}={type(value).__name__}")
                
                if detail_parts:
                    log_msg += f" - {', '.join(detail_parts)}"
            
            logger.debug(log_msg)
            
        except Exception as e:
            logger.warning(f"[{operation_id}] 数据库操作日志记录失败: {e}")

    @staticmethod
    def _record_transaction_failure(error_code: str, error_message: str, 
                                  transaction_id: str = None, trade_id: int = None,
                                  duration_ms: int = None, extra_data: dict = None) -> None:
        """Record transaction failure for monitoring"""
        
        # Map error codes to error types
        error_type_mapping = {
            TradeServiceV3.ErrorCodes.CONFIGURATION_ERROR: 'configuration_error',
            TradeServiceV3.ErrorCodes.BLOCKCHAIN_CONNECTION_ERROR: 'blockchain_error',
            TradeServiceV3.ErrorCodes.BLOCKHASH_RETRIEVAL_ERROR: 'blockchain_error',
            TradeServiceV3.ErrorCodes.INSTRUCTION_CREATION_ERROR: 'instruction_error',
            TradeServiceV3.ErrorCodes.TRANSACTION_BUILD_ERROR: 'transaction_build_error',
            TradeServiceV3.ErrorCodes.TRANSACTION_SERIALIZATION_ERROR: 'serialization_error',
            TradeServiceV3.ErrorCodes.TRANSACTION_VALIDATION_ERROR: 'validation_error',
            TradeServiceV3.ErrorCodes.DATABASE_ERROR: 'database_error',
            TradeServiceV3.ErrorCodes.INVALID_AMOUNT: 'validation_error',
            TradeServiceV3.ErrorCodes.ASSET_NOT_FOUND: 'validation_error',
            TradeServiceV3.ErrorCodes.ASSET_NOT_TRADEABLE: 'validation_error',
            TradeServiceV3.ErrorCodes.INSUFFICIENT_SUPPLY: 'validation_error'
        }
        
        error_type = error_type_mapping.get(error_code, 'unknown_error')
        
        # Record in transaction monitor
        transaction_monitor.record_transaction_attempt(
            TransactionStatus.FAILED,
            trade_id=trade_id,
            error_type=error_type,
            error_message=error_message,
            duration_ms=duration_ms
        )
        
        # Record in log aggregator
        log_data = {
            'error_type': error_type,
            'error_code': error_code,
            'trade_id': trade_id,
            'transaction_id': transaction_id,
            'duration_ms': duration_ms
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        transaction_log_aggregator.process_log_entry(
            'ERROR',
            f"Transaction creation failed: {error_message}",
            'TradeServiceV3',
            log_data
        )

    @staticmethod
    def _create_error_response(error_code: str, message: str, details: dict = None) -> dict:
        """
        创建标准化的错误响应
        
        Args:
            error_code: 错误代码
            message: 错误消息
            details: 可选的错误详情
            
        Returns:
            dict: 标准化的错误响应
        """
        response = {
            'success': False,
            'error_code': error_code,
            'message': message,
            'timestamp': time.time()
        }
        
        if details:
            response['details'] = details
            
        return response

    @staticmethod
    def _validate_configuration() -> dict:
        """
        验证所有必需的Solana配置参数
        
        Returns:
            dict: 包含验证结果和配置信息的字典
        """
        try:
            # 获取配置参数
            platform_treasury_address = current_app.config.get('PLATFORM_TREASURY_WALLET')
            payment_token_mint_address = current_app.config.get('PAYMENT_TOKEN_MINT_ADDRESS')
            payment_token_decimals = current_app.config.get('PAYMENT_TOKEN_DECIMALS', 6)
            solana_rpc_url = current_app.config.get('SOLANA_RPC_URL')
            
            missing_params = []
            invalid_params = []
            
            # 检查必需参数是否存在
            if not platform_treasury_address:
                missing_params.append('PLATFORM_TREASURY_WALLET')
            elif not validate_solana_address(platform_treasury_address):
                invalid_params.append('PLATFORM_TREASURY_WALLET: 无效的地址格式')
                
            if not payment_token_mint_address:
                missing_params.append('PAYMENT_TOKEN_MINT_ADDRESS')
            elif not validate_solana_address(payment_token_mint_address):
                invalid_params.append('PAYMENT_TOKEN_MINT_ADDRESS: 无效的代币铸造地址格式')
                
            if not solana_rpc_url:
                missing_params.append('SOLANA_RPC_URL')
            elif not (solana_rpc_url.startswith('http://') or solana_rpc_url.startswith('https://')):
                invalid_params.append('SOLANA_RPC_URL: 无效的RPC URL格式')
                
            # 验证小数位数
            try:
                decimals = int(payment_token_decimals)
                if decimals < 0 or decimals > 18:
                    invalid_params.append('PAYMENT_TOKEN_DECIMALS: 必须是0-18之间的整数')
            except (ValueError, TypeError):
                invalid_params.append('PAYMENT_TOKEN_DECIMALS: 必须是有效的整数')
                decimals = 6  # 默认值
            
            if missing_params or invalid_params:
                error_details = []
                if missing_params:
                    error_details.append(f"缺失参数: {', '.join(missing_params)}")
                if invalid_params:
                    error_details.append(f"无效参数: {', '.join(invalid_params)}")
                
                return {
                    'valid': False,
                    'message': '; '.join(error_details),
                    'missing_params': missing_params,
                    'invalid_params': invalid_params
                }
            
            return {
                'valid': True,
                'message': '所有配置参数验证通过',
                'config': {
                    'PLATFORM_TREASURY_WALLET': platform_treasury_address,
                    'PAYMENT_TOKEN_MINT_ADDRESS': payment_token_mint_address,
                    'PAYMENT_TOKEN_DECIMALS': decimals,
                    'SOLANA_RPC_URL': solana_rpc_url
                }
            }
            
        except Exception as e:
            logger.error(f"配置验证过程中发生异常: {e}", exc_info=True)
            return {
                'valid': False,
                'message': f'配置验证异常: {str(e)}',
                'missing_params': [],
                'invalid_params': []
            }



    @staticmethod
    def _create_transfer_instruction(
        buyer_address: str, 
        platform_address: str, 
        token_mint_address: str, 
        total_price: Decimal, 
        token_decimals: int,
        transaction_id: str
    ):
        """
        创建SPL代币转账指令，包含详细的参数验证和日志记录
        
        Args:
            buyer_address: 买方钱包地址
            platform_address: 平台收款地址
            token_mint_address: 代币铸造地址
            total_price: 总价格
            token_decimals: 代币小数位数
            transaction_id: 交易ID用于日志关联
            
        Returns:
            Instruction: SPL代币转账指令
            
        Raises:
            Exception: 指令创建失败时抛出异常
        """
        try:
            # 1. 验证输入参数
            if not buyer_address or not platform_address or not token_mint_address:
                raise ValueError("缺少必需的地址参数")
            
            if total_price <= 0:
                raise ValueError(f"无效的总价格: {total_price}")
            
            if token_decimals < 0 or token_decimals > 18:
                raise ValueError(f"无效的代币小数位数: {token_decimals}")
            
            logger.debug(f"[{transaction_id}] 输入参数验证通过")
            
            # 2. 转换地址为PublicKey并验证格式
            try:
                from solana.publickey import PublicKey
                
                buyer_pubkey = PublicKey(buyer_address)
                platform_pubkey = PublicKey(platform_address)
                payment_mint_pubkey = PublicKey(token_mint_address)
                
                # 验证地址不能相同
                if str(buyer_pubkey) == str(platform_pubkey):
                    raise ValueError("买方地址和平台地址不能相同")
                
                logger.debug(f"[{transaction_id}] 地址转换和验证成功")
                
            except Exception as e:
                raise ValueError(f"地址格式无效: {str(e)}")
            
            # 3. 验证使用正确的SPL代币程序ID
            spl_token_program_id = PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
            logger.debug(f"[{transaction_id}] 使用正确的SPL代币程序ID: {spl_token_program_id}")
            
            # 4. 获取关联代币账户 (ATA) - 确保使用正确的买方和平台钱包地址
            try:
                buyer_payment_token_ata = get_associated_token_address(buyer_pubkey, payment_mint_pubkey)
                platform_payment_token_ata = get_associated_token_address(platform_pubkey, payment_mint_pubkey)
                
                # 验证ATA地址不能相同
                if buyer_payment_token_ata == platform_payment_token_ata:
                    raise ValueError("买方和平台的关联代币账户地址不能相同")
                
                logger.debug(f"[{transaction_id}] ATA计算成功: 买方={str(buyer_payment_token_ata)[:8]}..., 平台={str(platform_payment_token_ata)[:8]}...")
                
            except Exception as e:
                raise ValueError(f"关联代币账户计算失败: {str(e)}")
            
            # 5. 修复金额计算 - 正确地从代币价格转换为USDC最小单位（乘以10^6）
            try:
                # 确保使用正确的小数位数进行转换
                if token_decimals != 6:
                    logger.warning(f"[{transaction_id}] 代币小数位数不是6: {token_decimals}, 但继续使用该值")
                
                # 使用Decimal进行精确计算，避免浮点数精度问题
                multiplier = Decimal(10) ** token_decimals
                amount_in_smallest_unit = int(total_price * multiplier)
                
                # 验证计算结果
                if amount_in_smallest_unit <= 0:
                    raise ValueError(f"计算后的转账金额无效: {amount_in_smallest_unit}")
                
                # 验证金额不会溢出（Solana u64最大值）
                max_u64 = 2**64 - 1
                if amount_in_smallest_unit > max_u64:
                    raise ValueError(f"转账金额超出u64最大值: {amount_in_smallest_unit} > {max_u64}")
                
                logger.debug(f"[{transaction_id}] 金额计算: 原始={total_price}, 最小单位={amount_in_smallest_unit}, 小数位数={token_decimals}, 乘数={multiplier}")
                
            except Exception as e:
                raise ValueError(f"金额计算失败: {str(e)}")
            
            # 6. 创建转账指令参数并验证
            try:
                transfer_params = TransferParams(
                    program_id=spl_token_program_id,
                    source=buyer_payment_token_ata,
                    dest=platform_payment_token_ata,
                    owner=buyer_pubkey,
                    amount=amount_in_smallest_unit
                )
                
                # 验证转账参数
                TradeServiceV3._validate_transfer_params(transfer_params, transaction_id)
                
                logger.debug(f"[{transaction_id}] 转账参数验证通过")
                
            except Exception as e:
                raise ValueError(f"转账参数创建或验证失败: {str(e)}")
            
            # 7. 创建转账指令
            try:
                instruction = transfer(transfer_params)
                
                # 验证指令创建成功
                if not instruction:
                    raise ValueError("转账指令创建失败，返回空指令")
                
                logger.debug(f"[{transaction_id}] 转账指令创建成功")
                
                # 8. 在添加到交易前验证转账指令参数
                TradeServiceV3._validate_transfer_instruction(instruction, transaction_id)
                
                return instruction
                
            except Exception as e:
                raise ValueError(f"转账指令创建失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"[{transaction_id}] 指令创建失败: {e}", exc_info=True)
            raise Exception(f"指令创建失败: {str(e)}")

    @staticmethod
    def _validate_transfer_params(transfer_params: TransferParams, transaction_id: str = None) -> None:
        """
        验证SPL代币转账参数
        
        Args:
            transfer_params: 转账参数
            transaction_id: 可选的交易ID用于日志关联
            
        Raises:
            ValueError: 参数验证失败时抛出异常
        """
        log_prefix = f"[{transaction_id}] " if transaction_id else ""
        
        try:
            # 验证程序ID
            expected_program_id = PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
            if str(transfer_params.program_id) != str(expected_program_id):
                raise ValueError(f"程序ID不正确: 期望 {expected_program_id}, 实际 {transfer_params.program_id}")
            
            # 验证源账户和目标账户不能相同
            if transfer_params.source == transfer_params.dest:
                raise ValueError("源账户和目标账户不能相同")
            
            # 验证金额大于0
            if transfer_params.amount <= 0:
                raise ValueError(f"转账金额必须大于0: {transfer_params.amount}")
            
            # 验证所有必需的Pubkey都存在
            if not transfer_params.source or not transfer_params.dest or not transfer_params.owner:
                raise ValueError("缺少必需的账户地址")
            
            logger.debug(f"{log_prefix}转账参数验证通过: 金额={transfer_params.amount}, 源={str(transfer_params.source)[:8]}..., 目标={str(transfer_params.dest)[:8]}...")
            
        except Exception as e:
            logger.error(f"{log_prefix}转账参数验证失败: {e}")
            raise ValueError(f"转账参数验证失败: {str(e)}")

    @staticmethod
    def _validate_transfer_instruction(instruction, transaction_id: str = None) -> None:
        """
        在添加到交易前验证转账指令参数
        
        Args:
            instruction: 转账指令
            transaction_id: 可选的交易ID用于日志关联
            
        Raises:
            ValueError: 指令验证失败时抛出异常
        """
        log_prefix = f"[{transaction_id}] " if transaction_id else ""
        
        try:
            # 验证指令存在
            if not instruction:
                raise ValueError("指令不能为空")
            
            # 验证指令有程序ID
            if not hasattr(instruction, 'program_id') or not instruction.program_id:
                raise ValueError("指令缺少程序ID")
            
            # 验证程序ID是正确的SPL代币程序
            expected_program_id = PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
            if str(instruction.program_id) != str(expected_program_id):
                raise ValueError(f"指令程序ID不正确: 期望 {expected_program_id}, 实际 {instruction.program_id}")
            
            # 验证指令有账户列表
            if not hasattr(instruction, 'accounts') or not instruction.accounts:
                raise ValueError("指令缺少账户列表")
            
            # 验证账户数量（SPL转账指令应该有3个账户：源、目标、所有者）
            if len(instruction.accounts) < 3:
                raise ValueError(f"指令账户数量不足: 期望至少3个, 实际 {len(instruction.accounts)}")
            
            # 验证指令有数据
            if not hasattr(instruction, 'data') or not instruction.data:
                raise ValueError("指令缺少数据")
            
            logger.debug(f"{log_prefix}转账指令验证通过: 程序ID={instruction.program_id}, 账户数={len(instruction.accounts)}, 数据长度={len(instruction.data)}")
            
        except Exception as e:
            logger.error(f"{log_prefix}转账指令验证失败: {e}")
            raise ValueError(f"转账指令验证失败: {str(e)}")

    @staticmethod
    def _validate_transaction(transaction: Transaction, transaction_id: str = None) -> bool:
        """
        在序列化前验证交易是否具有所有必需组件，包含全面的验证检查
        
        Args:
            transaction: 要验证的交易
            transaction_id: 可选的交易ID用于日志关联
            
        Returns:
            bool: 验证是否通过
        """
        log_prefix = f"[{transaction_id}] " if transaction_id else ""
        
        try:
            logger.debug(f"{log_prefix}开始全面交易验证")
            
            # 1. 基础组件验证
            if not TradeServiceV3._validate_transaction_components(transaction, transaction_id):
                return False
            
            # 2. 交易大小和限制验证
            if not TradeServiceV3._validate_transaction_limits(transaction, transaction_id):
                return False
            
            # 3. 指令参数和账户地址验证
            if not TradeServiceV3._validate_instruction_parameters(transaction, transaction_id):
                return False
            
            # 4. 序列化和反序列化验证
            if not TradeServiceV3._validate_transaction_serialization(transaction, transaction_id):
                return False
            
            logger.debug(f"{log_prefix}交易全面验证通过")
            return True
            
        except Exception as e:
            logger.error(f"{log_prefix}交易验证过程中发生错误: {e}", exc_info=True)
            return False

    @staticmethod
    def _validate_transaction_components(transaction: Transaction, transaction_id: str = None) -> bool:
        """
        验证交易是否具有所有必需的基础组件
        
        Args:
            transaction: 要验证的交易
            transaction_id: 可选的交易ID用于日志关联
            
        Returns:
            bool: 验证是否通过
        """
        log_prefix = f"[{transaction_id}] " if transaction_id else ""
        
        try:
            # 检查交易对象本身
            if not transaction:
                logger.error(f"{log_prefix}交易组件验证失败: 交易对象为空")
                return False
            
            # 检查交易消息
            if not hasattr(transaction, 'message') or not transaction.message:
                logger.error(f"{log_prefix}交易组件验证失败: 缺少交易消息")
                return False
            
            # 检查账户密钥
            if not hasattr(transaction.message, 'account_keys') or not transaction.message.account_keys:
                logger.error(f"{log_prefix}交易组件验证失败: 缺少账户密钥")
                return False
            
            # 检查付款人（第一个账户应该是付款人）
            if len(transaction.message.account_keys) == 0:
                logger.error(f"{log_prefix}交易组件验证失败: 账户密钥列表为空")
                return False
            
            # 检查指令
            if not hasattr(transaction.message, 'instructions') or not transaction.message.instructions:
                logger.error(f"{log_prefix}交易组件验证失败: 缺少指令")
                return False
            
            # 检查最新区块哈希
            if not hasattr(transaction.message, 'recent_blockhash') or not transaction.message.recent_blockhash:
                logger.error(f"{log_prefix}交易组件验证失败: 缺少最新区块哈希")
                return False
            
            # 验证区块哈希类型
            if not isinstance(transaction.message.recent_blockhash, Hash):
                logger.error(f"{log_prefix}交易组件验证失败: 区块哈希类型不正确 ({type(transaction.message.recent_blockhash)})")
                return False
            
            logger.debug(f"{log_prefix}交易基础组件验证通过")
            return True
            
        except Exception as e:
            logger.error(f"{log_prefix}交易组件验证过程中发生错误: {e}", exc_info=True)
            return False

    @staticmethod
    def _validate_transaction_limits(transaction: Transaction, transaction_id: str = None) -> bool:
        """
        验证交易大小限制和指令计数
        
        Args:
            transaction: 要验证的交易
            transaction_id: 可选的交易ID用于日志关联
            
        Returns:
            bool: 验证是否通过
        """
        log_prefix = f"[{transaction_id}] " if transaction_id else ""
        
        try:
            # 验证指令数量限制
            instruction_count = len(transaction.message.instructions)
            max_instructions = 10  # 合理的指令数量限制
            
            if instruction_count > max_instructions:
                logger.error(f"{log_prefix}交易限制验证失败: 指令数量过多 ({instruction_count} > {max_instructions})")
                return False
            
            if instruction_count == 0:
                logger.error(f"{log_prefix}交易限制验证失败: 指令数量为0")
                return False
            
            # 验证账户数量限制
            account_count = len(transaction.message.account_keys)
            max_accounts = 64  # Solana交易最大账户数量限制
            
            if account_count > max_accounts:
                logger.error(f"{log_prefix}交易限制验证失败: 账户数量过多 ({account_count} > {max_accounts})")
                return False
            
            if account_count == 0:
                logger.error(f"{log_prefix}交易限制验证失败: 账户数量为0")
                return False
            
            # 验证交易大小（序列化后不应超过1232字节）
            try:
                serialized_tx = transaction.serialize(verify_signatures=False)
                serialized_size = len(serialized_tx)
                max_tx_size = 1232  # Solana交易大小限制
                
                if serialized_size > max_tx_size:
                    logger.error(f"{log_prefix}交易限制验证失败: 交易大小过大 ({serialized_size} > {max_tx_size} 字节)")
                    return False
                
                if serialized_size == 0:
                    logger.error(f"{log_prefix}交易限制验证失败: 序列化交易大小为0")
                    return False
                
                logger.debug(f"{log_prefix}交易大小验证通过: {serialized_size} 字节")
                
            except Exception as e:
                logger.error(f"{log_prefix}交易大小验证失败: {e}")
                return False
            
            logger.debug(f"{log_prefix}交易限制验证通过: {instruction_count}个指令, {account_count}个账户, {serialized_size}字节")
            return True
            
        except Exception as e:
            logger.error(f"{log_prefix}交易限制验证过程中发生错误: {e}", exc_info=True)
            return False

    @staticmethod
    def _validate_instruction_parameters(transaction: Transaction, transaction_id: str = None) -> bool:
        """
        验证指令参数和账户地址的有效性
        
        Args:
            transaction: 要验证的交易
            transaction_id: 可选的交易ID用于日志关联
            
        Returns:
            bool: 验证是否通过
        """
        log_prefix = f"[{transaction_id}] " if transaction_id else ""
        
        try:
            # 验证每个指令
            for i, instruction in enumerate(transaction.message.instructions):
                logger.debug(f"{log_prefix}验证指令 {i+1}/{len(transaction.message.instructions)}")
                
                # 检查指令是否有程序ID
                if not hasattr(instruction, 'program_id_index') or instruction.program_id_index is None:
                    logger.error(f"{log_prefix}指令参数验证失败: 指令{i}缺少程序ID索引")
                    return False
                
                # 验证程序ID索引在有效范围内
                if instruction.program_id_index >= len(transaction.message.account_keys):
                    logger.error(f"{log_prefix}指令参数验证失败: 指令{i}程序ID索引超出范围 ({instruction.program_id_index} >= {len(transaction.message.account_keys)})")
                    return False
                
                # 获取程序ID并验证
                program_id = transaction.message.account_keys[instruction.program_id_index]
                if not program_id:
                    logger.error(f"{log_prefix}指令参数验证失败: 指令{i}程序ID为空")
                    return False
                
                # 检查指令是否有账户列表
                if not hasattr(instruction, 'accounts') or instruction.accounts is None:
                    logger.error(f"{log_prefix}指令参数验证失败: 指令{i}缺少账户列表")
                    return False
                
                # 验证账户索引在有效范围内
                for j, account_index in enumerate(instruction.accounts):
                    if account_index >= len(transaction.message.account_keys):
                        logger.error(f"{log_prefix}指令参数验证失败: 指令{i}账户{j}索引超出范围 ({account_index} >= {len(transaction.message.account_keys)})")
                        return False
                
                # 检查指令是否有数据
                if not hasattr(instruction, 'data') or instruction.data is None:
                    logger.error(f"{log_prefix}指令参数验证失败: 指令{i}缺少数据")
                    return False
                
                # 对于SPL代币转账指令，进行特殊验证
                expected_spl_program_id = PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
                if str(program_id) == str(expected_spl_program_id):
                    if not TradeServiceV3._validate_spl_transfer_instruction(instruction, transaction.message.account_keys, transaction_id, i):
                        return False
                
                logger.debug(f"{log_prefix}指令{i}验证通过: 程序ID={str(program_id)[:8]}..., 账户数={len(instruction.accounts)}, 数据长度={len(instruction.data)}")
            
            logger.debug(f"{log_prefix}所有指令参数验证通过")
            return True
            
        except Exception as e:
            logger.error(f"{log_prefix}指令参数验证过程中发生错误: {e}", exc_info=True)
            return False

    @staticmethod
    def _validate_spl_transfer_instruction(instruction, account_keys: list, transaction_id: str = None, instruction_index: int = 0) -> bool:
        """
        验证SPL代币转账指令的特定参数
        
        Args:
            instruction: SPL转账指令
            account_keys: 交易账户密钥列表
            transaction_id: 可选的交易ID用于日志关联
            instruction_index: 指令索引
            
        Returns:
            bool: 验证是否通过
        """
        log_prefix = f"[{transaction_id}] " if transaction_id else ""
        
        try:
            # SPL转账指令应该至少有3个账户：源、目标、所有者
            min_accounts = 3
            if len(instruction.accounts) < min_accounts:
                logger.error(f"{log_prefix}SPL转账指令验证失败: 指令{instruction_index}账户数量不足 ({len(instruction.accounts)} < {min_accounts})")
                return False
            
            # 验证源账户和目标账户不能相同
            source_index = instruction.accounts[0]
            dest_index = instruction.accounts[1]
            
            if source_index == dest_index:
                logger.error(f"{log_prefix}SPL转账指令验证失败: 指令{instruction_index}源账户和目标账户索引相同 ({source_index})")
                return False
            
            # 获取实际的账户地址并验证不相同
            source_account = account_keys[source_index]
            dest_account = account_keys[dest_index]
            
            if source_account == dest_account:
                logger.error(f"{log_prefix}SPL转账指令验证失败: 指令{instruction_index}源账户和目标账户地址相同")
                return False
            
            # 验证指令数据长度（SPL转账指令数据应该是12字节：1字节指令类型 + 8字节金额 + 可选的3字节小数位数）
            expected_data_lengths = [9, 12]  # 支持不同版本的SPL转账指令
            if len(instruction.data) not in expected_data_lengths:
                logger.warning(f"{log_prefix}SPL转账指令数据长度异常: 指令{instruction_index}数据长度={len(instruction.data)}, 期望={expected_data_lengths}")
                # 不返回False，因为不同版本的SPL指令可能有不同的数据长度
            
            # 验证指令数据的第一个字节应该是转账指令类型（通常是3）
            if len(instruction.data) > 0:
                instruction_type = instruction.data[0]
                expected_transfer_type = 3  # SPL转账指令类型
                if instruction_type != expected_transfer_type:
                    logger.warning(f"{log_prefix}SPL转账指令类型异常: 指令{instruction_index}类型={instruction_type}, 期望={expected_transfer_type}")
                    # 不返回False，因为可能有其他有效的转账指令类型
            
            logger.debug(f"{log_prefix}SPL转账指令{instruction_index}验证通过")
            return True
            
        except Exception as e:
            logger.error(f"{log_prefix}SPL转账指令验证过程中发生错误: {e}", exc_info=True)
            return False

    @staticmethod
    def _validate_transaction_serialization(transaction: Transaction, transaction_id: str = None) -> bool:
        """
        验证交易在序列化后能够成功反序列化
        
        Args:
            transaction: 要验证的交易
            transaction_id: 可选的交易ID用于日志关联
            
        Returns:
            bool: 验证是否通过
        """
        log_prefix = f"[{transaction_id}] " if transaction_id else ""
        
        try:
            logger.debug(f"{log_prefix}开始序列化验证")
            
            # 1. 序列化交易
            try:
                serialized_tx = transaction.serialize(verify_signatures=False)
                if not serialized_tx or len(serialized_tx) == 0:
                    logger.error(f"{log_prefix}序列化验证失败: 序列化结果为空")
                    return False
                
                logger.debug(f"{log_prefix}交易序列化成功: {len(serialized_tx)} 字节")
                
            except Exception as e:
                logger.error(f"{log_prefix}序列化验证失败: 序列化过程出错 - {e}")
                return False
            
            # 2. 尝试反序列化验证
            try:
                # 使用solders库反序列化交易
                deserialized_tx = Transaction.deserialize(serialized_tx)
                
                if not deserialized_tx:
                    logger.error(f"{log_prefix}序列化验证失败: 反序列化结果为空")
                    return False
                
                logger.debug(f"{log_prefix}交易反序列化成功")
                
            except Exception as e:
                logger.error(f"{log_prefix}序列化验证失败: 反序列化过程出错 - {e}")
                return False
            
            # 3. 验证反序列化后的交易与原交易的关键属性一致
            try:
                # 验证指令数量
                if len(deserialized_tx.message.instructions) != len(transaction.message.instructions):
                    logger.error(f"{log_prefix}序列化验证失败: 反序列化后指令数量不匹配 ({len(deserialized_tx.message.instructions)} != {len(transaction.message.instructions)})")
                    return False
                
                # 验证账户数量
                if len(deserialized_tx.message.account_keys) != len(transaction.message.account_keys):
                    logger.error(f"{log_prefix}序列化验证失败: 反序列化后账户数量不匹配 ({len(deserialized_tx.message.account_keys)} != {len(transaction.message.account_keys)})")
                    return False
                
                # 验证区块哈希
                if deserialized_tx.message.recent_blockhash != transaction.message.recent_blockhash:
                    logger.error(f"{log_prefix}序列化验证失败: 反序列化后区块哈希不匹配")
                    return False
                
                # 验证账户密钥
                for i, (orig_key, deser_key) in enumerate(zip(transaction.message.account_keys, deserialized_tx.message.account_keys)):
                    if orig_key != deser_key:
                        logger.error(f"{log_prefix}序列化验证失败: 反序列化后账户{i}不匹配")
                        return False
                
                logger.debug(f"{log_prefix}反序列化一致性验证通过")
                
            except Exception as e:
                logger.error(f"{log_prefix}序列化验证失败: 一致性检查出错 - {e}")
                return False
            
            # 4. 验证Base64编码和解码
            try:
                encoded_tx = base64.b64encode(serialized_tx).decode('utf-8')
                if not encoded_tx:
                    logger.error(f"{log_prefix}序列化验证失败: Base64编码结果为空")
                    return False
                
                # 验证Base64解码
                decoded_tx = base64.b64decode(encoded_tx)
                if decoded_tx != serialized_tx:
                    logger.error(f"{log_prefix}序列化验证失败: Base64编解码不一致")
                    return False
                
                logger.debug(f"{log_prefix}Base64编解码验证通过: {len(encoded_tx)} 字符")
                
            except Exception as e:
                logger.error(f"{log_prefix}序列化验证失败: Base64编解码出错 - {e}")
                return False
            
            logger.debug(f"{log_prefix}交易序列化验证完全通过")
            return True
            
        except Exception as e:
            logger.error(f"{log_prefix}序列化验证过程中发生错误: {e}", exc_info=True)
            return False