#!/usr/bin/env python3
"""
修复分享消息的权重值
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.share_message import ShareMessage
from app.extensions import db

def fix_weights():
    """修复权重值"""
    app = create_app()
    
    with app.app_context():
        try:
            # 权重映射规则
            weight_mapping = {
                1: 50,   # 低权重 -> 50
                2: 75,   # 中低权重 -> 75
                3: 100,  # 中权重 -> 100
                4: 125,  # 中高权重 -> 125
                5: 150,  # 高权重 -> 150
            }
            
            print("🔧 开始修复权重值...")
            print("-" * 80)
            
            messages = ShareMessage.query.all()
            updated_count = 0
            
            for msg in messages:
                old_weight = msg.weight
                new_weight = old_weight
                
                # 如果权重在旧的1-5范围内，进行映射
                if old_weight in weight_mapping:
                    new_weight = weight_mapping[old_weight]
                    msg.weight = new_weight
                    updated_count += 1
                    print(f"ID {msg.id:2d}: {old_weight:3d} -> {new_weight:3d} | {msg.message_type:12s} | {msg.content[:40]:40s}...")
                
                # 如果权重已经在合理范围内，保持不变
                elif old_weight in [50, 75, 100, 125, 150]:
                    print(f"ID {msg.id:2d}: {old_weight:3d} (保持) | {msg.message_type:12s} | {msg.content[:40]:40s}...")
                
                # 其他不合理的权重值，设置为默认值100
                else:
                    new_weight = 100
                    msg.weight = new_weight
                    updated_count += 1
                    print(f"ID {msg.id:2d}: {old_weight:3d} -> {new_weight:3d} (修正) | {msg.message_type:12s} | {msg.content[:40]:40s}...")
            
            # 提交更改
            if updated_count > 0:
                db.session.commit()
                print("-" * 80)
                print(f"✅ 成功更新了 {updated_count} 条消息的权重值")
            else:
                print("-" * 80)
                print("✅ 所有权重值都正常，无需更新")
            
            # 显示最终权重分布
            print("\n📊 修复后的权重分布:")
            weight_count = {}
            for msg in ShareMessage.query.all():
                weight = msg.weight
                if weight not in weight_count:
                    weight_count[weight] = 0
                weight_count[weight] += 1
            
            for weight in sorted(weight_count.keys()):
                print(f"权重 {weight}: {weight_count[weight]} 条消息")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 修复权重失败: {str(e)}")
            return False

if __name__ == "__main__":
    fix_weights() 