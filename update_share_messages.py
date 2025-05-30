#!/usr/bin/env python3
"""
更新分享消息为更现代化的内容
"""

from app import create_app
from app.models.share_message import ShareMessage
from app.extensions import db

def update_share_messages():
    """更新分享消息内容"""
    app = create_app()
    
    with app.app_context():
        # 删除现有的分享消息
        ShareMessage.query.delete()
        db.session.commit()
        
        # 添加新的现代化分享消息
        new_messages = [
            {
                'content': '🚀 发现优质RWA资产！真实世界资产数字化投资新机遇，透明度高、收益稳定。通过我的专属链接投资，我们都能获得长期收益！',
                'weight': 3,
                'is_active': True
            },
            {
                'content': '💎 区块链遇见传统资产！这个RWA项目通过区块链技术让实体资产投资更加透明安全。一起探索数字化投资的未来吧！',
                'weight': 2,
                'is_active': True
            },
            {
                'content': '🌟 投资新趋势：真实世界资产代币化！房产、艺术品等实体资产现在可以通过区块链投资，门槛更低，流动性更强！',
                'weight': 2,
                'is_active': True
            },
            {
                'content': '🔗 RWA投资社区邀请！真实世界资产代币化让投资更加透明、便捷。通过专属链接加入，共享投资智慧！',
                'weight': 2,
                'is_active': True
            },
            {
                'content': '📊 传统投资的区块链革命！RWA（真实世界资产）让房产、商品等实体投资变得更加民主化。点击探索投资新世界！',
                'weight': 1,
                'is_active': True
            }
        ]
        
        for msg_data in new_messages:
            message = ShareMessage(
                content=msg_data['content'],
                weight=msg_data['weight'],
                is_active=msg_data['is_active']
            )
            db.session.add(message)
        
        db.session.commit()
        print(f"✅ 成功更新了 {len(new_messages)} 条分享消息")
        
        # 验证更新结果
        updated_messages = ShareMessage.query.all()
        print("\n📝 更新后的分享消息:")
        for i, msg in enumerate(updated_messages, 1):
            print(f"{i}. {msg.content}")

if __name__ == '__main__':
    update_share_messages() 