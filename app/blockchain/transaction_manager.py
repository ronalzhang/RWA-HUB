#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Solana交易管理器 - 提供完善的交易构建、签名验证、广播和确认跟踪功能
"""

import logging
import time
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from app.utils.solana_compat.connection import Connection
from app.utils.solana_compat.publickey import PublicKey
from app.utils.solana_compat.transaction import Transaction, TransactionInstruction
from app.utils.solana_compat.keypair import Keypair
from app.config import Config
from app.extensions import db
from app.models.trade import Trade
from app.blockchain.solana_service import (
    get_solana_connection, execute_with_retry, 
    get_recent_blockhash_with_retry, validate_solana_address
)

logger = logging.getLogger(__name__)

class TransactionStatus(Enum):
    """交易状态枚举"""
    CREATED = "created"
    SIGNED = "signed"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FINALIZED = "finalized"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class TransactionConfig:
    """交易配置"""
    max_retries: int = 3
    confirmation_timeout: int = 60
    check_interval: float = 2.0
    fee_payer: Optional[str] = None
    compute_unit_limit: Optional[int] = None
    compute_unit_price: Optional[int] = None

@dataclass
class TransactionResult:
    """交易结果"""
    success: bool
    signature: Optional[str] = None
    status: TransactionStatus = TransactionStatus.CREATED
    error: Optional[str] = None
    confirmations: int = 0
    slot: Optional[int] = None
    fee_paid: Optional[int] = None
    execution_time: Optional[float] = None

class SolanaTransactionManager:
    """Solana交易管理器"""
    
    def __init__(self, config: TransactionConfig = None):
        self.config = config or TransactionConfig()
        self.pending_transactions = {}  # 跟踪待处理的交易
        
    def create_transfer_transaction(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        token_mint: str = None,
        memo: str = None
    ) -> Tuple[Transaction, str]:
        """
        创建转账交易
        
        Args:
            from_address: 发送方地址
            to_address: 接收方地址
            amount: 转账金额
            token_mint: 代币铸造地址（None表示SOL转账）
            memo: 交易备注
            
        Returns:
            Tuple[Transaction, str]: 交易对象和交易ID
        """
        logger.info(f"创建转账交易: {from_address} -> {to_address}, 金额: {amount}")
        
        # 验证输入参数
        if not validate_solana_address(from_address):
            raise ValueError(f"无效的发送方地址: {from_address}")
        
        if not validate_solana_address(to_address):
            raise ValueError(f"无效的接收方地址: {to_address}")
        
        if amount <= 0:
            raise ValueError("转账金额必须大于0")
        
        # 创建交易
        transaction = Transaction()
        
        # 获取最新区块哈希
        blockhash = get_recent_blockhash_with_retry()
        transaction.recent_blockhash = blockhash
        
        # 设置费用支付者
        fee_payer = PublicKey(self.config.fee_payer or from_address)
        transaction.fee_payer = fee_payer
        
        if token_mint:
            # 代币转账
            self._add_token_transfer_instruction(
                transaction, from_address, to_address, amount, token_mint
            )
        else:
            # SOL转账
            self._add_sol_transfer_instruction(
                transaction, from_address, to_address, amount
            )
        
        # 添加备注指令
        if memo:
            self._add_memo_instruction(transaction, memo, from_address)
        
        # 生成交易ID
        transaction_id = self._generate_transaction_id(transaction)
        
        logger.info(f"交易创建完成，ID: {transaction_id}")
        return transaction, transaction_id
    
    def _add_token_transfer_instruction(
        self,
        transaction: Transaction,
        from_address: str,
        to_address: str,
        amount: float,
        token_mint: str
    ):
        """添加代币转账指令"""
        from app.utils.solana_compat.token.instructions import create_transfer_instruction
        
        # 转换地址为PublicKey
        sender = PublicKey(from_address)
        recipient = PublicKey(to_address)
        mint = PublicKey(token_mint)
        
        # 获取关联代币账户
        sender_token_account = self._get_associated_token_address(sender, mint)
        recipient_token_account = self._get_associated_token_address(recipient, mint)
        
        # 转换金额为最小单位
        # USDC有6位小数
        amount_lamports = int(amount * 1_000_000)
        
        # 创建转账指令
        transfer_instruction = create_transfer_instruction(
            source=sender_token_account,
            dest=recipient_token_account,
            owner=sender,
            amount=amount_lamports
        )
        
        transaction.add(transfer_instruction)
        logger.debug(f"添加代币转账指令: {amount} {token_mint}")
    
    def _add_sol_transfer_instruction(
        self,
        transaction: Transaction,
        from_address: str,
        to_address: str,
        amount: float
    ):
        """添加SOL转账指令"""
        from app.utils.solana_compat.system_program import SystemProgram
        
        sender = PublicKey(from_address)
        recipient = PublicKey(to_address)
        
        # 转换SOL为lamports
        amount_lamports = int(amount * 1_000_000_000)
        
        # 创建系统转账指令
        transfer_instruction = SystemProgram.transfer(
            from_pubkey=sender,
            to_pubkey=recipient,
            lamports=amount_lamports
        )
        
        transaction.add(transfer_instruction)
        logger.debug(f"添加SOL转账指令: {amount} SOL")
    
    def _add_memo_instruction(self, transaction: Transaction, memo: str, signer: str):
        """添加备注指令"""
        memo_program_id = PublicKey('MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr')
        
        memo_instruction = TransactionInstruction(
            program_id=memo_program_id,
            data=memo.encode('utf-8'),
            keys=[{
                'pubkey': PublicKey(signer),
                'isSigner': True,
                'isWritable': False
            }]
        )
        
        transaction.add(memo_instruction)
        logger.debug(f"添加备注指令: {memo}")
    
    def _get_associated_token_address(self, owner: PublicKey, mint: PublicKey) -> PublicKey:
        """获取关联代币账户地址"""
        try:
            from app.utils.solana_compat.token.instructions import get_associated_token_address
            return get_associated_token_address(owner, mint)
        except ImportError:
            # 如果无法导入，使用手动计算
            return self._calculate_associated_token_address(owner, mint)
    
    def _calculate_associated_token_address(self, owner: PublicKey, mint: PublicKey) -> PublicKey:
        """手动计算关联代币账户地址"""
        TOKEN_PROGRAM_ID = PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
        ASSOCIATED_TOKEN_PROGRAM_ID = PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
        
        seeds = [
            owner.to_bytes(),
            TOKEN_PROGRAM_ID.to_bytes(),
            mint.to_bytes(),
        ]
        
        address, _ = PublicKey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM_ID)
        return address
    
    def _generate_transaction_id(self, transaction: Transaction) -> str:
        """生成交易ID"""
        # 使用交易内容的哈希作为ID
        tx_data = transaction.serialize_message()
        tx_hash = hashlib.sha256(tx_data).hexdigest()
        return f"tx_{tx_hash[:16]}"
    
    def sign_transaction(
        self,
        transaction: Transaction,
        private_key: bytes = None,
        keypair: Keypair = None
    ) -> TransactionResult:
        """
        签名交易
        
        Args:
            transaction: 要签名的交易
            private_key: 私钥字节
            keypair: 密钥对对象
            
        Returns:
            TransactionResult: 签名结果
        """
        try:
            logger.info("开始签名交易")
            
            if keypair:
                signer = keypair
            elif private_key:
                signer = Keypair.from_secret_key(private_key)
            else:
                raise ValueError("必须提供私钥或密钥对")
            
            # 签名交易
            transaction.sign(signer)
            
            logger.info("交易签名完成")
            return TransactionResult(
                success=True,
                status=TransactionStatus.SIGNED
            )
            
        except Exception as e:
            logger.error(f"交易签名失败: {e}")
            return TransactionResult(
                success=False,
                status=TransactionStatus.FAILED,
                error=str(e)
            )
    
    def submit_transaction(
        self,
        transaction: Transaction,
        transaction_id: str = None
    ) -> TransactionResult:
        """
        提交交易到网络
        
        Args:
            transaction: 已签名的交易
            transaction_id: 交易ID
            
        Returns:
            TransactionResult: 提交结果
        """
        def _submit():
            logger.info(f"提交交易到网络: {transaction_id}")
            
            connection = get_solana_connection()
            if not connection:
                raise Exception("无法获取Solana连接")
            
            # 发送交易
            result = connection.send_transaction(transaction)
            
            if isinstance(result, dict) and 'error' in result:
                raise Exception(f"交易提交失败: {result['error']}")
            
            signature = result if isinstance(result, str) else str(result)
            
            # 记录待处理交易
            if transaction_id:
                self.pending_transactions[transaction_id] = {
                    'signature': signature,
                    'submitted_at': datetime.utcnow(),
                    'status': TransactionStatus.SUBMITTED
                }
            
            logger.info(f"交易提交成功，签名: {signature}")
            
            return TransactionResult(
                success=True,
                signature=signature,
                status=TransactionStatus.SUBMITTED
            )
        
        try:
            return execute_with_retry("提交交易", _submit, max_retries=self.config.max_retries)
        except Exception as e:
            logger.error(f"交易提交失败: {e}")
            return TransactionResult(
                success=False,
                status=TransactionStatus.FAILED,
                error=str(e)
            )
    
    def wait_for_confirmation(
        self,
        signature: str,
        timeout: int = None
    ) -> TransactionResult:
        """
        等待交易确认
        
        Args:
            signature: 交易签名
            timeout: 超时时间（秒）
            
        Returns:
            TransactionResult: 确认结果
        """
        timeout = timeout or self.config.confirmation_timeout
        logger.info(f"等待交易确认: {signature}, 超时: {timeout}秒")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                status = self._check_transaction_status(signature)
                
                if status['confirmed']:
                    logger.info(f"交易已确认: {signature}")
                    return TransactionResult(
                        success=True,
                        signature=signature,
                        status=TransactionStatus.CONFIRMED,
                        confirmations=status['confirmations'],
                        slot=status.get('slot')
                    )
                
                if status.get('error'):
                    logger.error(f"交易失败: {signature}, 错误: {status['error']}")
                    return TransactionResult(
                        success=False,
                        signature=signature,
                        status=TransactionStatus.FAILED,
                        error=status['error']
                    )
                
                logger.debug(f"交易待确认: {signature}, 状态: {status.get('status', 'unknown')}")
                time.sleep(self.config.check_interval)
                
            except Exception as e:
                logger.warning(f"检查交易状态时出错: {e}")
                time.sleep(self.config.check_interval)
        
        logger.warning(f"交易确认超时: {signature}")
        return TransactionResult(
            success=False,
            signature=signature,
            status=TransactionStatus.TIMEOUT,
            error="交易确认超时"
        )
    
    def _check_transaction_status(self, signature: str) -> Dict[str, Any]:
        """检查交易状态"""
        def _check():
            connection = get_solana_connection()
            if not connection:
                raise Exception("无法获取Solana连接")
            
            status_result = connection.get_signature_status(signature)
            
            if status_result is None:
                return {
                    "confirmed": False,
                    "confirmations": 0,
                    "status": "pending",
                    "error": None
                }
            
            confirmed = status_result.get("confirmationStatus") in ["confirmed", "finalized"]
            confirmations = status_result.get("confirmations", 0)
            error = status_result.get("err")
            
            return {
                "confirmed": confirmed,
                "confirmations": confirmations,
                "status": status_result.get("confirmationStatus", "unknown"),
                "error": error,
                "slot": status_result.get("slot")
            }
        
        return execute_with_retry("检查交易状态", _check, max_retries=2)
    
    def execute_complete_transaction(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        private_key: bytes = None,
        keypair: Keypair = None,
        token_mint: str = None,
        memo: str = None
    ) -> TransactionResult:
        """
        执行完整的交易流程（创建、签名、提交、确认）
        
        Args:
            from_address: 发送方地址
            to_address: 接收方地址
            amount: 转账金额
            private_key: 私钥字节
            keypair: 密钥对对象
            token_mint: 代币铸造地址
            memo: 交易备注
            
        Returns:
            TransactionResult: 最终结果
        """
        start_time = time.time()
        
        try:
            # 1. 创建交易
            transaction, transaction_id = self.create_transfer_transaction(
                from_address, to_address, amount, token_mint, memo
            )
            
            # 2. 签名交易
            sign_result = self.sign_transaction(transaction, private_key, keypair)
            if not sign_result.success:
                return sign_result
            
            # 3. 提交交易
            submit_result = self.submit_transaction(transaction, transaction_id)
            if not submit_result.success:
                return submit_result
            
            # 4. 等待确认
            confirm_result = self.wait_for_confirmation(submit_result.signature)
            
            # 计算执行时间
            execution_time = time.time() - start_time
            confirm_result.execution_time = execution_time
            
            return confirm_result
            
        except Exception as e:
            logger.error(f"执行完整交易流程失败: {e}")
            return TransactionResult(
                success=False,
                status=TransactionStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def get_transaction_fee_estimate(self, transaction: Transaction) -> Dict[str, Any]:
        """
        估算交易费用
        
        Args:
            transaction: 交易对象
            
        Returns:
            dict: 费用估算结果
        """
        try:
            connection = get_solana_connection()
            if not connection:
                raise Exception("无法获取Solana连接")
            
            # 获取费用信息
            # 在实际实现中，这里应该调用Solana的费用估算API
            
            # 基础费用计算
            signature_count = len(transaction.signatures) if hasattr(transaction, 'signatures') else 1
            base_fee = 5000 * signature_count  # 每个签名5000 lamports
            
            # 计算单位费用（如果设置了）
            compute_unit_fee = 0
            if self.config.compute_unit_limit and self.config.compute_unit_price:
                compute_unit_fee = self.config.compute_unit_limit * self.config.compute_unit_price
            
            total_fee = base_fee + compute_unit_fee
            
            return {
                'base_fee_lamports': base_fee,
                'compute_unit_fee_lamports': compute_unit_fee,
                'total_fee_lamports': total_fee,
                'total_fee_sol': total_fee / 1_000_000_000,
                'signature_count': signature_count
            }
            
        except Exception as e:
            logger.error(f"估算交易费用失败: {e}")
            return {
                'error': str(e),
                'estimated_fee_lamports': 5000,  # 默认估算
                'estimated_fee_sol': 0.000005
            }
    
    def create_batch_transactions(
        self,
        transactions_data: List[Dict[str, Any]]
    ) -> List[Tuple[Transaction, str]]:
        """
        批量创建交易
        
        Args:
            transactions_data: 交易数据列表
            
        Returns:
            List[Tuple[Transaction, str]]: 交易对象和ID的列表
        """
        results = []
        
        for tx_data in transactions_data:
            try:
                transaction, tx_id = self.create_transfer_transaction(
                    from_address=tx_data['from_address'],
                    to_address=tx_data['to_address'],
                    amount=tx_data['amount'],
                    token_mint=tx_data.get('token_mint'),
                    memo=tx_data.get('memo')
                )
                results.append((transaction, tx_id))
                
            except Exception as e:
                logger.error(f"创建批量交易失败: {e}")
                # 可以选择继续处理其他交易或者停止
                continue
        
        logger.info(f"批量创建交易完成，成功: {len(results)}/{len(transactions_data)}")
        return results
    
    def get_pending_transactions(self) -> Dict[str, Any]:
        """获取待处理交易列表"""
        return {
            'count': len(self.pending_transactions),
            'transactions': dict(self.pending_transactions)
        }
    
    def cleanup_old_transactions(self, max_age_hours: int = 24):
        """清理旧的待处理交易记录"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for tx_id, tx_info in self.pending_transactions.items():
            if tx_info['submitted_at'] < cutoff_time:
                to_remove.append(tx_id)
        
        for tx_id in to_remove:
            del self.pending_transactions[tx_id]
        
        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个旧交易记录")

# 全局交易管理器实例
transaction_manager = SolanaTransactionManager()