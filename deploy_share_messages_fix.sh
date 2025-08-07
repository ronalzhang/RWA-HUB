#!/bin/bash

# 分享消息管理模块修复部署脚本
echo "🚀 开始部署分享消息管理模块修复..."

# 1. 拉取最新代码
echo "📥 拉取最新代码..."
git pull origin main

# 2. 执行数据库修复
echo "🔧 执行数据库修复..."
python3 -c "
from app import create_app
from app.extensions import db
from sqlalchemy import text

def fix_share_messages_table():
    app = create_app()
    with app.app_context():
        try:
            print('🔧 开始修复分享消息表结构...')
            
            # 检查 message_type 字段是否存在
            result = db.session.execute(text('''
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name=\'share_messages\' AND column_name=\'message_type\'
            '''))
            columns = result.fetchall()
            
            if not columns:
                print('❌ message_type 字段不存在，正在添加...')
                
                # 添加 message_type 字段
                db.session.execute(text('''
                    ALTER TABLE share_messages 
                    ADD COLUMN message_type VARCHAR(50) NOT NULL DEFAULT \'share_content\'
                '''))
                
                db.session.commit()
                print('✅ 已添加 message_type 字段')
            else:
                print('✅ message_type 字段已存在')
            
            # 检查数据
            result = db.session.execute(text('SELECT COUNT(*) FROM share_messages'))
            count = result.scalar()
            print(f'📊 当前消息数量: {count}')
            
            if count == 0:
                print('🔄 初始化默认分享消息...')
                
                # 插入默认的分享内容消息
                share_messages = [
                    '🚀 发现优质RWA资产！真实世界资产数字化投资新机遇，透明度高、收益稳定。',
                    '💎 投资RWA资产，享受实物资产带来的稳定收益！区块链技术保障，安全可靠。',
                    '🏆 分享赚佣金！邀请好友投资，您可获得高达35%的推广佣金！',
                    '🤝 好东西就要和朋友分享！发送您的专属链接，让更多朋友加入这个投资社区。',
                    '🔥 发现好机会就要分享！邀请好友一起投资这个优质资产，共同见证财富增长！'
                ]
                
                for i, content in enumerate(share_messages):
                    db.session.execute(text('''
                        INSERT INTO share_messages (content, message_type, weight, is_active, created_at, updated_at)
                        VALUES (:content, \'share_content\', :weight, true, NOW(), NOW())
                    '''), {
                        'content': content,
                        'weight': 100 - i * 10
                    })
                
                # 插入奖励计划消息
                reward_messages = [
                    '一次分享，终身收益 - 无限下级35%分成',
                    '💰 推荐好友即享35%超高佣金，人人都是赚钱达人！',
                    '🎯 多级分销，收益无上限！您的下线越多，收益越丰厚！'
                ]
                
                for i, content in enumerate(reward_messages):
                    db.session.execute(text('''
                        INSERT INTO share_messages (content, message_type, weight, is_active, created_at, updated_at)
                        VALUES (:content, \'reward_plan\', :weight, true, NOW(), NOW())
                    '''), {
                        'content': content,
                        'weight': 80 - i * 10
                    })
                
                db.session.commit()
                
                result = db.session.execute(text('SELECT COUNT(*) FROM share_messages'))
                new_count = result.scalar()
                print(f'✅ 已初始化 {new_count} 条默认分享消息')
            
            print('🎉 分享消息表结构修复完成！')
            
        except Exception as e:
            print(f'❌ 修复失败: {e}')
            db.session.rollback()
            raise

fix_share_messages_table()
"

# 3. 重启应用服务
echo "🔄 重启应用服务..."
if command -v systemctl &> /dev/null; then
    sudo systemctl restart rwa-hub
    echo "✅ 已重启 rwa-hub 服务"
elif command -v supervisorctl &> /dev/null; then
    sudo supervisorctl restart rwa-hub
    echo "✅ 已重启 rwa-hub 服务"
else
    echo "⚠️  请手动重启应用服务"
fi

echo "🎉 分享消息管理模块修复部署完成！"
echo ""
echo "📋 修复内容："
echo "  ✅ 修复了 share_messages 表结构"
echo "  ✅ 添加了 message_type 字段"
echo "  ✅ 初始化了默认分享消息数据"
echo "  ✅ 分享消息管理功能现已正常工作"
echo ""
echo "🔗 访问路径："
echo "  - 分享消息管理: /admin/v2/share-messages"
echo "  - 分销系统配置: /admin/v2/commission"