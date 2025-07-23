#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
分享消息类型迁移脚本
用法: python scripts/migrate_share_message_types.py
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.admin import SystemConfig
from app.models.share_message import ShareMessage

def migrate_system_configs():
    """迁移系统配置数据"""
    print("开始迁移系统配置数据...")
    
    configs = [
        {"key": "PLATFORM_FEE_ADDRESS", "value": "6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b", "desc": "平台收款地址"},
        {"key": "ASSET_CREATION_FEE_ADDRESS", "value": "6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b", "desc": "资产创建收款地址"},
        {"key": "ASSET_CREATION_FEE_AMOUNT", "value": "0.02", "desc": "资产创建费用(USDC)"},
        {"key": "PLATFORM_FEE_BASIS_POINTS", "value": "350", "desc": "平台费率(基点)"},
        {"key": "PLATFORM_FEE_RATE", "value": "0.035", "desc": "平台费率(小数)"},
        {"key": "SOLANA_RPC_URL", "value": "https://api.mainnet-beta.solana.com", "desc": "Solana RPC节点"},
        {"key": "SOLANA_USDC_MINT", "value": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "desc": "USDC Mint地址"},
        {"key": "SOLANA_PROGRAM_ID", "value": "2TsURTNQXyqHLB2bfbzFME7HkSMLWueYPjqXBBy2u1wP", "desc": "Solana程序ID"},
        {"key": "SOLANA_PRIVATE_KEY_ENCRYPTED", "value": "", "desc": "加密的Solana私钥(待管理员设置)"},
    ]
    
    for cfg in configs:
        existing = SystemConfig.query.filter_by(config_key=cfg["key"]).first()
        if not existing:
            config = SystemConfig(
                config_key=cfg["key"],
                config_value=cfg["value"],
                description=cfg["desc"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(config)
            print(f"添加配置: {cfg['key']}")
        else:
            existing.config_value = cfg["value"]
            existing.updated_at = datetime.utcnow()
            print(f"更新配置: {cfg['key']}")

def migrate_share_messages():
    """迁移分享消息数据"""
    print("开始迁移分享消息数据...")
    
    # 添加分享消息数据（如果不存在）
    messages = [
        {"content": "🚀 发现优质RWA资产！真实世界资产数字化投资新机遇，透明度高、收益稳定。立即体验：", "type": "reward_plan", "weight": 10},
        {"content": "💎 投资真实世界资产，数字化时代的理财新选择！RWA-HUB为您提供透明、安全的投资平台。", "type": "share_content", "weight": 8},
        {"content": "🏠 不动产投资新玩法！通过区块链技术，轻松参与优质房地产项目投资。", "type": "reward_plan", "weight": 9},
        {"content": "🌟 RWA数字化投资平台，让传统资产焕发新活力！收益稳定，风险可控。", "type": "share_content", "weight": 7},
        {"content": "💰 智能分佣系统，35%无限级收益分成！邀请好友一起投资，共享财富增长。", "type": "share_content", "weight": 6},
        {"content": "🔐 区块链技术保障，资产透明可查，投资更放心！RWA-HUB值得信赖。", "type": "share_content", "weight": 8},
        {"content": "📈 多元化投资组合，降低风险提升收益！RWA资产配置的最佳选择。", "type": "share_content", "weight": 5},
        {"content": "🎯 专业团队严选资产，每一个项目都经过深度尽调，为您的投资保驾护航。", "type": "share_content", "weight": 7}
    ]
    
    for msg_data in messages:
        existing = ShareMessage.query.filter_by(content=msg_data["content"]).first()
        if not existing:
            message = ShareMessage(
                content=msg_data["content"],
                message_type=msg_data["type"],
                weight=msg_data["weight"],
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(message)
            print(f"添加分享消息: {msg_data['content'][:30]}...")
        else:
            # 更新现有消息的类型（修复之前的错误分类）
            existing.message_type = msg_data["type"]
            existing.weight = msg_data["weight"]
            existing.updated_at = datetime.utcnow()
            print(f"更新分享消息类型: {msg_data['content'][:30]}... -> {msg_data['type']}")

def main():
    """主函数"""
    app = create_app()
    
    with app.app_context():
        print("=== RWA-HUB 数据迁移脚本 ===")
        print(f"执行时间: {datetime.now()}")
        
        try:
            # 迁移系统配置
            migrate_system_configs()
            
            # 迁移分享消息
            migrate_share_messages()
            
            # 提交数据库更改
            db.session.commit()
            print("\n✅ 数据迁移完成！")
            
            # 验证结果
            config_count = SystemConfig.query.count()
            message_count = ShareMessage.query.count()
            share_content_count = ShareMessage.query.filter_by(message_type="share_content").count()
            reward_plan_count = ShareMessage.query.filter_by(message_type="reward_plan").count()
            
            print(f"📊 迁移结果:")
            print(f"  - 系统配置: {config_count} 条")
            print(f"  - 分享消息: {message_count} 条")
            print(f"  - 分享内容消息: {share_content_count} 条")
            print(f"  - 奖励计划消息: {reward_plan_count} 条")
            
        except Exception as e:
            print(f"❌ 迁移失败: {str(e)}")
            db.session.rollback()
            return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)