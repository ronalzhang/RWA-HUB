#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库优化脚本 - 任务5.3数据库查询性能优化
执行数据库索引创建和性能优化
"""

import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from migrations.add_performance_indexes import optimize_database_performance

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/database_optimization.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    try:
        logger.info("开始数据库优化...")
        
        # 创建Flask应用
        app = create_app()
        
        with app.app_context():
            # 执行数据库优化
            result = optimize_database_performance()
            
            if result['success']:
                logger.info("数据库优化成功完成!")
                logger.info(f"索引优化结果: {result['index_optimization']}")
                logger.info(f"表分析结果: {result['table_analysis']}")
                
                print("\n" + "="*60)
                print("数据库优化完成!")
                print("="*60)
                print(f"创建索引数量: {result['index_optimization']['created_indexes']}")
                print(f"跳过索引数量: {result['index_optimization']['skipped_indexes']}")
                print(f"分析表数量: {result['table_analysis']['analyzed_tables']}")
                print(f"完成时间: {result['completed_at']}")
                print("="*60)
                
            else:
                logger.error(f"数据库优化失败: {result['error']}")
                print(f"\n数据库优化失败: {result['error']}")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"执行数据库优化时发生错误: {str(e)}", exc_info=True)
        print(f"\n执行数据库优化时发生错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()