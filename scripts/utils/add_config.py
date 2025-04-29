#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 获取数据库连接字符串，如果没有则使用默认值
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rwa_hub_user:password@localhost/rwa_hub")

# 创建数据库引擎
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# 定义Config模型
class Config(Base):
    __tablename__ = 'configs'
    
    key = Column(String(255), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Config(key='{self.key}', value='{self.value}')>"

# 确保数据库表存在
Base.metadata.create_all(engine)

def add_or_update_config(key, value, description=None):
    """添加或更新配置项到数据库"""
    session = Session()
    try:
        # 检查配置项是否已存在
        config = session.query(Config).filter_by(key=key).first()
        
        if config:
            # 更新现有配置
            config.value = value
            if description:
                config.description = description
            config.updated_at = datetime.utcnow()
            action = "更新"
        else:
            # 创建新配置
            config = Config(key=key, value=value, description=description)
            session.add(config)
            action = "添加"
            
        session.commit()
        print(f"成功{action}配置项: {key} = {value}")
        return True
    except Exception as e:
        session.rollback()
        print(f"数据库操作失败: {str(e)}")
        return False
    finally:
        session.close()

def update_env_file(key, value):
    """更新.env文件中的配置项"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    # 检查.env文件是否存在
    if not os.path.exists(env_path):
        # 创建新的.env文件
        with open(env_path, 'w') as f:
            f.write(f"{key}={value}\n")
        print(f"创建新的.env文件并添加: {key}={value}")
        return True
        
    # 读取当前.env文件内容
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # 查找并更新配置项
    key_found = False
    new_lines = []
    
    for line in lines:
        if line.strip() and '=' in line:
            env_key, env_value = line.strip().split('=', 1)
            if env_key == key:
                new_lines.append(f"{key}={value}\n")
                key_found = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # 如果配置项不存在，则添加到文件末尾
    if not key_found:
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        new_lines.append(f"{key}={value}\n")
    
    # 写回.env文件
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"已更新.env文件: {key}={value}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="添加或更新配置项到数据库和.env文件")
    parser.add_argument("key", help="配置项的键名")
    parser.add_argument("value", help="配置项的值")
    parser.add_argument("--description", "-d", help="配置项的描述（可选）")
    
    args = parser.parse_args()
    
    # 添加/更新数据库配置
    db_success = add_or_update_config(args.key, args.value, args.description)
    
    # 更新.env文件
    env_success = update_env_file(args.key, args.value)
    
    if db_success and env_success:
        print(f"配置项 {args.key} 已成功更新到数据库和.env文件")
        sys.exit(0)
    else:
        print("配置更新过程中出现错误")
        sys.exit(1) 