import sys
import os

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # 检查trades表结构
    print("检查 trades 表结构...")
    
    # 使用原生SQL查询表结构
    with db.engine.connect() as connection:
        # 检查表是否存在
        result = connection.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'trades'
            );
        """))
        exists = result.scalar()
        
        if not exists:
            print("trades 表不存在!")
            sys.exit(1)
        
        # 获取表中的所有列
        result = connection.execute(text("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'trades';
        """))
        
        print("\ntrades 表结构:")
        print("{:<20} {:<20} {:<10}".format("列名", "数据类型", "最大长度"))
        print("-" * 50)
        
        for row in result:
            column_name = row[0]
            data_type = row[1]
            max_length = row[2] if row[2] is not None else "N/A"
            print("{:<20} {:<20} {:<10}".format(column_name, data_type, max_length))
        
        # 检查trader_address列长度
        result = connection.execute(text("""
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'trades' AND column_name = 'trader_address';
        """))
        
        trader_address_length = result.scalar()
        print(f"\ntrader_address 列最大长度: {trader_address_length}")
        
        # 检查tx_hash列长度
        result = connection.execute(text("""
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'trades' AND column_name = 'tx_hash';
        """))
        
        tx_hash_length = result.scalar()
        print(f"tx_hash 列最大长度: {tx_hash_length}")
        
        # 检查模型定义与数据库是否一致
        from app.models import Trade
        
        # 获取模型中定义的列
        model_columns = Trade.__table__.columns
        
        print("\n模型定义:")
        for column in model_columns:
            column_name = column.name
            column_type = str(column.type)
            print(f"{column_name}: {column_type}")
        
        # 检查 trader_address 列是否存在并且与前端传递的地址兼容
        print("\n测试地址是否超出列长度:")
        test_address = "EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR"
        if trader_address_length is not None and len(test_address) > trader_address_length:
            print(f"警告: 测试地址长度({len(test_address)})超过trader_address列最大长度({trader_address_length})")
        else:
            print(f"测试地址长度({len(test_address)})符合trader_address列最大长度({trader_address_length})") 