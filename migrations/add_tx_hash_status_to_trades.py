import sys
import os
from sqlalchemy import text

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app, db
from app.models import Trade

app = create_app()

def run_migration():
    with app.app_context():
        # 检查tx_hash列是否存在
        has_tx_hash = False
        has_status = False
        has_gas_used = False
        
        # 检查列是否存在
        try:
            # 使用PostgreSQL特定查询检查列是否存在
            with db.engine.begin() as connection:
                # 检查tx_hash列
                result = connection.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'trades' AND column_name = 'tx_hash'
                """))
                has_tx_hash = result.rowcount > 0
                
                # 检查status列
                result = connection.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'trades' AND column_name = 'status'
                """))
                has_status = result.rowcount > 0
                
                # 检查gas_used列
                result = connection.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'trades' AND column_name = 'gas_used'
                """))
                has_gas_used = result.rowcount > 0
        except Exception as e:
            print(f"检查列时出错: {e}")
        
        print(f"检查列状态：tx_hash: {has_tx_hash}, status: {has_status}, gas_used: {has_gas_used}")
        
        # 添加所需的列
        with db.engine.begin() as connection:
            if not has_tx_hash:
                print("正在添加 tx_hash 列...")
                connection.execute(text("ALTER TABLE trades ADD COLUMN tx_hash VARCHAR(100);"))
                print("tx_hash 列添加成功")
            
            if not has_status:
                print("正在添加 status 列...")
                connection.execute(text("ALTER TABLE trades ADD COLUMN status VARCHAR(20) DEFAULT 'pending';"))
                print("status 列添加成功")
            
            if not has_gas_used:
                print("正在添加 gas_used 列...")
                connection.execute(text("ALTER TABLE trades ADD COLUMN gas_used NUMERIC;"))
                print("gas_used 列添加成功")
        
        print("数据库迁移完成")

if __name__ == '__main__':
    run_migration() 