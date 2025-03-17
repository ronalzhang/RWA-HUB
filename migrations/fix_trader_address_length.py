import sys
import os
from sqlalchemy import text

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app, db

app = create_app()

def run_migration():
    with app.app_context():
        print("开始修复trader_address列长度...")
        
        # 检查当前列长度
        with db.engine.connect() as connection:
            result = connection.execute(text("""
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'trades' AND column_name = 'trader_address';
            """))
            
            current_length = result.scalar()
            print(f"当前trader_address列长度: {current_length}")
            
            if current_length < 64:
                print(f"需要增加列长度到64...")
                
                # 执行ALTER语句增加列长度
                connection.execute(text("""
                    ALTER TABLE trades 
                    ALTER COLUMN trader_address TYPE VARCHAR(64);
                """))
                
                print("trader_address列长度修改完成")
                
                # 验证修改是否成功
                result = connection.execute(text("""
                    SELECT character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = 'trades' AND column_name = 'trader_address';
                """))
                
                new_length = result.scalar()
                print(f"修改后trader_address列长度: {new_length}")
            else:
                print(f"trader_address列长度已经足够，无需修改")
        
        print("迁移完成")

if __name__ == "__main__":
    run_migration() 