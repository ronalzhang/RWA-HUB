import sys
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 确保可以导入app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """运行迁移脚本，添加缺少的列到用户推荐和佣金表"""
    app = create_app()
    
    with app.app_context():
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        conn = engine.connect()
        try:
            trans = conn.begin()

            # 检查 user_referrals 表是否存在
            check_table_sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_referrals'
            );
            """
            result = conn.execute(text(check_table_sql))
            table_exists = result.scalar()
            
            if not table_exists:
                logger.info("user_referrals 表不存在，创建表...")
                create_user_referrals_sql = """
                CREATE TABLE user_referrals (
                    id SERIAL PRIMARY KEY,
                    user_address VARCHAR(64) NOT NULL,
                    referrer_address VARCHAR(64) NOT NULL,
                    referral_level INTEGER NOT NULL DEFAULT 1,
                    referral_code VARCHAR(50),
                    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    first_connected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
                conn.execute(text(create_user_referrals_sql))
                logger.info("user_referrals 表创建成功")
            else:
                # 检查列是否存在，如果不存在则添加
                columns_to_check = ['first_connected_at', 'created_at']
                for column in columns_to_check:
                    check_column_sql = f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'user_referrals' AND column_name = '{column}'
                    );
                    """
                    result = conn.execute(text(check_column_sql))
                    column_exists = result.scalar()
                    
                    if not column_exists:
                        logger.info(f"添加 {column} 列到 user_referrals 表")
                        add_column_sql = f"""
                        ALTER TABLE user_referrals 
                        ADD COLUMN {column} TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
                        """
                        conn.execute(text(add_column_sql))
                        logger.info(f"{column} 列添加成功")
                    else:
                        logger.info(f"{column} 列已存在")

            # 检查 commission_records 表是否存在
            check_table_sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'commission_records'
            );
            """
            result = conn.execute(text(check_table_sql))
            table_exists = result.scalar()
            
            if not table_exists:
                logger.info("commission_records 表不存在，创建表...")
                create_commission_records_sql = """
                CREATE TABLE commission_records (
                    id SERIAL PRIMARY KEY,
                    transaction_id INTEGER NOT NULL,
                    asset_id INTEGER NOT NULL,
                    recipient_address VARCHAR(64) NOT NULL,
                    amount FLOAT NOT NULL,
                    currency VARCHAR(10) NOT NULL DEFAULT 'USDC',
                    commission_type VARCHAR(20) NOT NULL,
                    referral_level INTEGER,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    tx_hash VARCHAR(100),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
                conn.execute(text(create_commission_records_sql))
                logger.info("commission_records 表创建成功")
            else:
                # 检查列是否存在，如果不存在则添加
                columns_to_check = ['tx_hash', 'referral_level']
                for column in columns_to_check:
                    check_column_sql = f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'commission_records' AND column_name = '{column}'
                    );
                    """
                    result = conn.execute(text(check_column_sql))
                    column_exists = result.scalar()
                    
                    if not column_exists:
                        if column == 'tx_hash':
                            logger.info(f"添加 {column} 列到 commission_records 表")
                            add_column_sql = f"""
                            ALTER TABLE commission_records 
                            ADD COLUMN {column} VARCHAR(100);
                            """
                        elif column == 'referral_level':
                            logger.info(f"添加 {column} 列到 commission_records 表")
                            add_column_sql = f"""
                            ALTER TABLE commission_records 
                            ADD COLUMN {column} INTEGER;
                            """
                        conn.execute(text(add_column_sql))
                        logger.info(f"{column} 列添加成功")
                    else:
                        logger.info(f"{column} 列已存在")
                
                # 检查 transaction_id 列的类型
                check_column_type_sql = """
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'commission_records' 
                AND column_name = 'transaction_id';
                """
                result = conn.execute(text(check_column_type_sql))
                data_type = result.scalar()
                
                if data_type != 'integer':
                    logger.info(f"修改 transaction_id 列的类型为 INTEGER")
                    
                    # 创建临时表用于修改列类型
                    drop_temp_table_sql = "DROP TABLE IF EXISTS temp_commission_records;"
                    conn.execute(text(drop_temp_table_sql))
                    
                    # 创建临时表
                    create_temp_table_sql = """
                    CREATE TABLE temp_commission_records AS 
                    SELECT * FROM commission_records;
                    """
                    conn.execute(text(create_temp_table_sql))
                    
                    # 修改原表的列类型
                    alter_column_sql = """
                    ALTER TABLE commission_records 
                    ALTER COLUMN transaction_id TYPE INTEGER USING transaction_id::integer;
                    """
                    conn.execute(text(alter_column_sql))
                    
                    logger.info("transaction_id 列类型修改成功")

            # 检查 distribution_settings 表是否存在
            check_table_sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'distribution_settings'
            );
            """
            result = conn.execute(text(check_table_sql))
            table_exists = result.scalar()
            
            if not table_exists:
                logger.info("distribution_settings 表不存在，创建表...")
                create_distribution_settings_sql = """
                CREATE TABLE distribution_settings (
                    id SERIAL PRIMARY KEY,
                    level INTEGER NOT NULL,
                    commission_rate FLOAT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
                conn.execute(text(create_distribution_settings_sql))
                logger.info("distribution_settings 表创建成功")
                
                # 插入初始数据
                insert_data_sql = """
                INSERT INTO distribution_settings (level, commission_rate, is_active)
                VALUES 
                    (1, 0.3, TRUE),
                    (2, 0.15, TRUE),
                    (3, 0.05, TRUE);
                """
                conn.execute(text(insert_data_sql))
                logger.info("已插入初始分销比例设置")
            
            trans.commit()
            logger.info("迁移完成!")
            
        except SQLAlchemyError as e:
            trans.rollback()
            logger.error(f"迁移失败: {str(e)}")
        finally:
            conn.close()

if __name__ == "__main__":
    run_migration() 