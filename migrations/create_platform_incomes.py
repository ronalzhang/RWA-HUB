import sys
import os
import traceback
from sqlalchemy import text

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app, db

app = create_app()

def run_migration():
    with app.app_context():
        print("开始创建platform_incomes表...")
        
        try:
            # 检查表是否已存在
            with db.engine.connect() as connection:
                # 开始事务
                transaction = connection.begin()
                try:
                    result = connection.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'platform_incomes'
                        );
                    """))
                    
                    table_exists = result.scalar()
                    
                    if table_exists:
                        print("platform_incomes表已经存在，跳过创建")
                        transaction.commit()
                        return
                    
                    print("表不存在，开始创建...")
                    
                    # 创建platform_incomes表
                    connection.execute(text("""
                        CREATE TABLE platform_incomes (
                            id SERIAL PRIMARY KEY,
                            type INTEGER NOT NULL,
                            amount FLOAT NOT NULL,
                            description VARCHAR(200),
                            asset_id INTEGER REFERENCES assets(id),
                            related_id INTEGER,
                            tx_hash VARCHAR(100),
                            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """))
                    
                    print("platform_incomes表创建成功")
                    
                    # 创建索引
                    connection.execute(text("""
                        CREATE INDEX ix_platform_incomes_type ON platform_incomes (type);
                    """))
                    
                    print("platform_incomes表索引创建成功")
                    
                    # 验证表创建
                    result = connection.execute(text("""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_name = 'platform_incomes';
                    """))
                    
                    if result.scalar() > 0:
                        print("验证成功: platform_incomes表已创建")
                    else:
                        print("验证失败: platform_incomes表未创建")
                    
                    # 提交事务
                    transaction.commit()
                    print("事务已提交")
                    
                except Exception as e:
                    transaction.rollback()
                    print(f"发生错误，事务已回滚: {str(e)}")
                    print(traceback.format_exc())
                    raise
        
        except Exception as e:
            print(f"迁移过程中发生错误: {str(e)}")
            print(traceback.format_exc())
            raise
        
        print("迁移完成")

if __name__ == "__main__":
    try:
        run_migration()
        print("迁移脚本成功执行完毕")
    except Exception as e:
        print(f"迁移脚本执行失败: {str(e)}")
        sys.exit(1) 