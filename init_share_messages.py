#!/usr/bin/env python3
"""
初始化分享消息系统
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.share_message import ShareMessage

def init_share_messages():
    """初始化分享消息系统"""
    app = create_app()
    
    with app.app_context():
        try:
            # 创建表
            db.create_all()
            print("✅ 数据库表创建成功")
            
            # 检查是否已有数据
            existing_count = ShareMessage.query.count()
            if existing_count > 0:
                print(f"✅ 已有 {existing_count} 条分享消息，无需初始化")
                return True
            
            # 创建默认分享消息
            default_messages = [
                # 分享内容消息
                {
                    "content": "🚀 发现优质RWA资产！真实世界资产数字化投资新机遇，透明度高、收益稳定。通过我的专属链接投资，我们都能获得长期收益！",
                    "message_type": "share_content",
                    "weight": 100,
                    "is_active": True
                },
                {
                    "content": "🌟 投资新趋势：真实世界资产代币化！房产、艺术品等实体资产现在可以通过区块链投资，门槛更低，流动性更强！",
                    "message_type": "share_content",
                    "weight": 90,
                    "is_active": True
                },
                {
                    "content": "💎 传统投资的数字化革命正在到来！RWA资产让您以更小的资金参与大型实体投资，收益透明可追溯！",
                    "message_type": "share_content",
                    "weight": 80,
                    "is_active": True
                },
                {
                    "content": "🔥 抓住RWA投资风口！将房地产、商品等实物资产数字化，让投资更加透明、便捷。立即体验未来投资方式！",
                    "message_type": "share_content",
                    "weight": 70,
                    "is_active": True
                },
                {
                    "content": "⚡ RWA资产投资新机遇！突破传统投资限制，小额也能参与大宗商品、房地产投资，收益稳定可期！",
                    "message_type": "share_content",
                    "weight": 60,
                    "is_active": True
                },
                # 奖励计划文案
                {
                    "content": "一次分享，终身收益 - 无限下级20%分成",
                    "message_type": "reward_plan",
                    "weight": 100,
                    "is_active": True
                },
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
            
            # 批量创建消息
            created_count = 0
            for msg_data in default_messages:
                message = ShareMessage(
                    content=msg_data["content"],
                    message_type=msg_data["message_type"],
                    weight=msg_data["weight"],
                    is_active=msg_data["is_active"]
                )
                db.session.add(message)
                created_count += 1
            
            # 提交到数据库
            db.session.commit()
            print(f"✅ 成功创建 {created_count} 条默认分享消息")
            
            # 验证创建结果
            share_content_count = ShareMessage.query.filter_by(message_type="share_content").count()
            reward_plan_count = ShareMessage.query.filter_by(message_type="reward_plan").count()
            
            print(f"📊 统计信息：")
            print(f"   - 分享内容消息：{share_content_count} 条")
            print(f"   - 奖励计划文案：{reward_plan_count} 条")
            print(f"   - 总计：{share_content_count + reward_plan_count} 条")
            
            return True
            
        except Exception as e:
            print(f"❌ 初始化失败：{e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("🚀 开始初始化分享消息系统...")
    success = init_share_messages()
    
    if success:
        print("\n🎉 初始化成功完成！")
        print("📝 现在您可以：")
        print("   1. 测试分享消息API：curl http://localhost:9000/api/share-messages/random")
        print("   2. 测试奖励计划API：curl http://localhost:9000/api/share-reward-plan/random") 
        print("   3. 访问后台管理界面进行配置")
    else:
        print("\n💥 初始化失败，请检查错误信息")
        sys.exit(1) 