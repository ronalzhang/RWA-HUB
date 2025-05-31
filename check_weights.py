#!/usr/bin/env python3
"""
检查分享消息的权重值分布
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.share_message import ShareMessage

def check_weights():
    """检查消息权重分布"""
    app = create_app()
    
    with app.app_context():
        try:
            messages = ShareMessage.query.all()
            print("🔍 现有消息权重分布:")
            print("-" * 80)
            
            weight_count = {}
            for msg in messages:
                weight = msg.weight
                if weight not in weight_count:
                    weight_count[weight] = 0
                weight_count[weight] += 1
                
                print(f"ID: {msg.id:2d} | 权重: {weight:3d} | 类型: {msg.message_type:12s} | 内容: {msg.content[:40]:40s}...")
            
            print("-" * 80)
            print("📊 权重分布统计:")
            for weight in sorted(weight_count.keys()):
                print(f"权重 {weight}: {weight_count[weight]} 条消息")
                
            print(f"\n✅ 总计: {len(messages)} 条消息")
            
            return True
            
        except Exception as e:
            print(f"❌ 检查权重失败: {str(e)}")
            return False

if __name__ == "__main__":
    check_weights() 