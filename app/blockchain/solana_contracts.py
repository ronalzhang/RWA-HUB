#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Solana智能合约集成接口
提供与RWA-Hub智能合约交互的功能
"""

import json
import logging
import os
import subprocess
from typing import Dict, Any, Optional, Tuple

from app.config import Config

# 获取日志记录器
logger = logging.getLogger(__name__)

# 智能合约ID
RWA_TRADE_PROGRAM_ID = Config.RWA_TRADE_PROGRAM_ID or "rwaHubTradeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
RWA_DIVIDEND_PROGRAM_ID = Config.RWA_DIVIDEND_PROGRAM_ID or "rwaHubDividendXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# Node.js脚本路径
CONTRACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "rwahub-contracts"))
BACKEND_SCRIPT = os.path.join(CONTRACTS_DIR, "scripts", "backend-integration.js")

def _run_node_command(command: str, *args) -> Dict[str, Any]:
    """
    执行Node.js命令并解析结果
    
    Args:
        command (str): 命令名称
        *args: 命令参数
        
    Returns:
        Dict[str, Any]: 命令执行结果
    """
    try:
        cmd = ["node", BACKEND_SCRIPT, command]
        cmd.extend([str(arg) for arg in args])
        
        logger.info(f"执行Node.js命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=CONTRACTS_DIR
        )
        
        if result.returncode != 0:
            error = json.loads(result.stderr)
            logger.error(f"Node.js命令执行失败: {error.get('message')}")
            return {
                "success": False,
                "error": error.get("message", "未知错误"),
                "details": error
            }
        
        output = json.loads(result.stdout)
        logger.info(f"Node.js命令执行成功: {output}")
        return {
            "success": True,
            "result": output
        }
        
    except Exception as e:
        logger.error(f"执行Node.js命令时出错: {str(e)}")
        return {
            "success": False,
            "error": f"执行Node.js命令时出错: {str(e)}"
        }

def initialize_asset(token_mint: str, price: int, total_supply: int, platform_fee: int = 35) -> Dict[str, Any]:
    """
    初始化资产
    
    Args:
        token_mint (str): 代币铸造地址
        price (int): 代币价格（以USDC计价）
        total_supply (int): 总供应量
        platform_fee (int, optional): 平台手续费（以千分比表示，例如35表示3.5%）
        
    Returns:
        Dict[str, Any]: 初始化结果，包括资产账户地址
    """
    return _run_node_command("initAsset", token_mint, price, total_supply, platform_fee)

def buy_asset(asset_address: str, buyer_address: str, amount: int) -> Dict[str, Any]:
    """
    购买资产
    
    Args:
        asset_address (str): 资产账户地址
        buyer_address (str): 买家地址
        amount (int): 购买数量
        
    Returns:
        Dict[str, Any]: 购买结果，包括交易签名
    """
    return _run_node_command("buyAsset", asset_address, buyer_address, amount)

def create_dividend(
    creator_address: str, 
    asset_token_mint: str, 
    total_amount: int, 
    deadline_days: int = 30, 
    platform_fee: int = 35
) -> Dict[str, Any]:
    """
    创建分红
    
    Args:
        creator_address (str): 创建者地址
        asset_token_mint (str): 资产代币铸造地址
        total_amount (int): 总分红金额
        deadline_days (int, optional): 截止时间（天数）
        platform_fee (int, optional): 平台手续费（以千分比表示，例如35表示3.5%）
        
    Returns:
        Dict[str, Any]: 创建结果，包括分红账户地址
    """
    return _run_node_command(
        "createDividend", 
        creator_address, 
        asset_token_mint, 
        total_amount, 
        deadline_days, 
        platform_fee
    )

def claim_dividend(dividend_address: str, holder_address: str, amount: int) -> Dict[str, Any]:
    """
    领取分红
    
    Args:
        dividend_address (str): 分红账户地址
        holder_address (str): 持有者地址
        amount (int): 领取金额
        
    Returns:
        Dict[str, Any]: 领取结果，包括交易签名
    """
    return _run_node_command("claimDividend", dividend_address, holder_address, amount)

def is_contracts_available() -> bool:
    """
    检查智能合约是否可用
    
    Returns:
        bool: 智能合约是否可用
    """
    if not os.path.exists(BACKEND_SCRIPT):
        logger.warning(f"智能合约脚本不存在: {BACKEND_SCRIPT}")
        return False
        
    # 检查PROGRAM_ID是否为默认值
    if RWA_TRADE_PROGRAM_ID.find("XXXXXXX") != -1 or RWA_DIVIDEND_PROGRAM_ID.find("XXXXXXX") != -1:
        logger.warning("智能合约ID未设置")
        return False
        
    return True 