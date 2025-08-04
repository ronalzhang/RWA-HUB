#!/usr/bin/env python3
"""
管理员权限验证问题诊断脚本
用于检查数据库中的管理员数据和验证逻辑
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """获取数据库连接URL"""
    # 从配置中获取数据库URL，默认使用生产环境的数据库（因为测试环境共享数据库）
    db_url = os.environ.get('DATABASE_URL', 'postgresql://rwa_hub_user:password@localhost/rwa_hub')
    logger.info(f"使用数据库URL: {db_url}")
    return db_url

def diagnose_admin_users():
    """诊断管理员用户数据"""
    try:
        # 创建数据库连接
        db_url = get_database_url()
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        logger.info("=" * 60)
        logger.info("开始诊断管理员权限验证问题")
        logger.info("=" * 60)
        
        # 1. 检查admin_users表是否存在
        logger.info("\n1. 检查admin_users表结构...")
        try:
            result = session.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'admin_users'
                ORDER BY ordinal_position;
            """))
            columns = result.fetchall()
            
            if columns:
                logger.info("✅ admin_users表存在，结构如下:")
                for col in columns:
                    logger.info(f"   - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
            else:
                logger.error("❌ admin_users表不存在!")
                return False
                
        except Exception as e:
            logger.error(f"❌ 检查表结构失败: {e}")
            return False
        
        # 2. 查询所有管理员用户
        logger.info("\n2. 查询所有管理员用户...")
        try:
            result = session.execute(text("""
                SELECT id, wallet_address, username, role, created_at, last_login
                FROM admin_users 
                ORDER BY created_at;
            """))
            admins = result.fetchall()
            
            if admins:
                logger.info(f"✅ 找到 {len(admins)} 个管理员用户:")
                for admin in admins:
                    logger.info(f"   ID: {admin[0]}")
                    logger.info(f"   钱包地址: {admin[1]}")
                    logger.info(f"   用户名: {admin[2] or '未设置'}")
                    logger.info(f"   角色: {admin[3]}")
                    logger.info(f"   创建时间: {admin[4]}")
                    logger.info(f"   最后登录: {admin[5] or '从未登录'}")
                    logger.info("   " + "-" * 40)
            else:
                logger.warning("⚠️  没有找到任何管理员用户!")
                
        except Exception as e:
            logger.error(f"❌ 查询管理员用户失败: {e}")
            return False
        
        # 3. 检查特定钱包地址（如果提供）
        test_addresses = [
            # 这里可以添加需要测试的钱包地址
            "0x1234567890123456789012345678901234567890",  # 示例以太坊地址
            "11111111111111111111111111111111",  # 示例Solana地址
        ]
        
        logger.info("\n3. 测试特定钱包地址验证...")
        for address in test_addresses:
            try:
                # 测试以太坊地址（小写匹配）
                if address.startswith('0x'):
                    result = session.execute(text("""
                        SELECT id, wallet_address, role 
                        FROM admin_users 
                        WHERE LOWER(wallet_address) = LOWER(:address)
                    """), {"address": address})
                else:
                    # 测试Solana地址（精确匹配）
                    result = session.execute(text("""
                        SELECT id, wallet_address, role 
                        FROM admin_users 
                        WHERE wallet_address = :address
                    """), {"address": address})
                
                admin = result.fetchone()
                if admin:
                    logger.info(f"✅ 地址 {address} 是管理员 (ID: {admin[0]}, 角色: {admin[2]})")
                else:
                    logger.info(f"❌ 地址 {address} 不是管理员")
                    
            except Exception as e:
                logger.error(f"❌ 测试地址 {address} 失败: {e}")
        
        # 4. 检查数据库连接和权限
        logger.info("\n4. 检查数据库连接和权限...")
        try:
            result = session.execute(text("SELECT current_user, current_database();"))
            db_info = result.fetchone()
            logger.info(f"✅ 数据库连接正常")
            logger.info(f"   当前用户: {db_info[0]}")
            logger.info(f"   当前数据库: {db_info[1]}")
            
        except Exception as e:
            logger.error(f"❌ 数据库连接检查失败: {e}")
            return False
        
        # 5. 生成诊断报告
        logger.info("\n" + "=" * 60)
        logger.info("诊断报告总结")
        logger.info("=" * 60)
        
        if admins:
            logger.info("✅ 数据库连接正常")
            logger.info("✅ admin_users表存在且有数据")
            logger.info(f"✅ 共有 {len(admins)} 个管理员用户")
            
            # 提供修复建议
            logger.info("\n🔧 修复建议:")
            logger.info("1. 检查前端发送的钱包地址格式是否正确")
            logger.info("2. 确认管理员地址在数据库中的存储格式")
            logger.info("3. 检查认证装饰器的逻辑是否正确")
            logger.info("4. 验证session管理是否正常工作")
            
        else:
            logger.warning("⚠️  没有管理员用户，需要添加管理员")
            logger.info("\n🔧 修复步骤:")
            logger.info("1. 添加管理员用户到数据库")
            logger.info("2. 确保钱包地址格式正确")
            logger.info("3. 重新测试管理员登录")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ 诊断过程中发生错误: {e}")
        return False

def add_test_admin(wallet_address, username="Test Admin"):
    """添加测试管理员用户"""
    try:
        db_url = get_database_url()
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        logger.info(f"\n添加测试管理员: {wallet_address}")
        
        # 检查是否已存在
        if wallet_address.startswith('0x'):
            result = session.execute(text("""
                SELECT id FROM admin_users 
                WHERE LOWER(wallet_address) = LOWER(:address)
            """), {"address": wallet_address})
        else:
            result = session.execute(text("""
                SELECT id FROM admin_users 
                WHERE wallet_address = :address
            """), {"address": wallet_address})
        
        existing = result.fetchone()
        if existing:
            logger.info(f"⚠️  管理员 {wallet_address} 已存在 (ID: {existing[0]})")
            return True
        
        # 添加新管理员
        session.execute(text("""
            INSERT INTO admin_users (wallet_address, username, role, created_at, updated_at)
            VALUES (:address, :username, 'admin', NOW(), NOW())
        """), {
            "address": wallet_address,
            "username": username
        })
        
        session.commit()
        logger.info(f"✅ 成功添加管理员: {wallet_address}")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ 添加管理员失败: {e}")
        return False

if __name__ == "__main__":
    print("RWA平台管理员权限诊断工具")
    print("=" * 50)
    
    # 运行诊断
    success = diagnose_admin_users()
    
    if success:
        print("\n✅ 诊断完成")
        
        # 询问是否需要添加测试管理员
        if len(sys.argv) > 1 and sys.argv[1] == "--add-admin":
            if len(sys.argv) > 2:
                wallet_address = sys.argv[2]
                username = sys.argv[3] if len(sys.argv) > 3 else "Test Admin"
                add_test_admin(wallet_address, username)
            else:
                print("\n使用方法: python diagnose_admin_auth.py --add-admin <钱包地址> [用户名]")
    else:
        print("\n❌ 诊断失败")
        sys.exit(1)