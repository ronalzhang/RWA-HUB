#!/usr/bin/env python3
"""
添加新的奖励计划文案到生产环境
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.share_message import ShareMessage

def add_reward_plan_messages():
    """添加新的奖励计划文案"""
    app = create_app()
    
    with app.app_context():
        try:
            # 新的奖励计划文案
            new_messages = [
                {
                    "content": "建立收益网络，所有下线终身20%分成",
                    "message_type": "reward_plan",
                    "weight": 90,
                    "is_active": True
                },
                {
                    "content": "分享即赚钱，团队收益永久分成",
                    "message_type": "reward_plan",
                    "weight": 80,
                    "is_active": True
                },
                {
                    "content": "智能分润：分享一次，终身享受团队收益",
                    "message_type": "reward_plan",
                    "weight": 70,
                    "is_active": True
                },
                {
                    "content": "无限层级分成，一次分享终身受益",
                    "message_type": "reward_plan",
                    "weight": 60,
                    "is_active": True
                },
                {
                    "content": "推广越多赚越多，下级收益持续分成",
                    "message_type": "reward_plan",
                    "weight": 50,
                    "is_active": True
                }
            ]
            
            added_count = 0
            for msg_data in new_messages:
                # 检查是否已存在相同内容
                existing = ShareMessage.query.filter_by(content=msg_data["content"]).first()
                if not existing:
                    message = ShareMessage(
                        content=msg_data["content"],
                        message_type=msg_data["message_type"],
                        weight=msg_data["weight"],
                        is_active=msg_data["is_active"]
                    )
                    db.session.add(message)
                    added_count += 1
                    print(f"✅ 添加文案：{msg_data['content']}")
                else:
                    print(f"⚠️  文案已存在：{msg_data['content']}")
            
            # 提交到数据库
            db.session.commit()
            print(f"\n✅ 成功添加 {added_count} 条新的奖励计划文案")
            
            # 统计结果
            total_messages = ShareMessage.query.count()
            reward_plan_count = ShareMessage.query.filter_by(message_type="reward_plan").count()
            share_content_count = ShareMessage.query.filter_by(message_type="share_content").count()
            
            print(f"\n📊 当前统计：")
            print(f"   - 总消息数：{total_messages}")
            print(f"   - 奖励计划文案：{reward_plan_count}")
            print(f"   - 分享内容消息：{share_content_count}")
            
            return True
            
        except Exception as e:
            print(f"❌ 添加失败：{e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("🚀 开始添加新的奖励计划文案...")
    success = add_reward_plan_messages()
    
    if success:
        print("\n🎉 添加成功完成！")
        print("📝 现在可以测试新的API：")
        print("   curl http://47.236.39.134:9000/api/share-reward-plan/random")
    else:
        print("\n💥 添加失败，请检查错误信息")
        sys.exit(1) 