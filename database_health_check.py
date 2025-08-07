#!/usr/bin/env python3
"""
RWA-HUB 5.0 数据库健康检查脚本
定期执行以监控数据库性能和数据完整性
"""

import psycopg2
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'database': 'rwa_hub',
    'user': 'rwa_hub_user',
    'password': 'password',
    'port': 5432
}

class DatabaseHealthChecker:
    def __init__(self, config: Dict):
        self.config = config
        self.conn = None
        
    def connect(self):
        """连接数据库"""
        try:
            self.conn = psycopg2.connect(**self.config)
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.conn:
            self.conn.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Tuple]:
        """执行查询"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def check_table_sizes(self):
        """检查表大小"""
        print("📊 表大小统计:")
        print("-" * 50)
        
        query = """
        SELECT 
            schemaname as schema,
            tablename as table,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
            pg_stat_get_tuples_inserted(c.oid) as inserts,
            pg_stat_get_tuples_updated(c.oid) as updates,
            pg_stat_get_tuples_deleted(c.oid) as deletes
        FROM pg_tables pt
        LEFT JOIN pg_class c ON c.relname = pt.tablename
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        LIMIT 10;
        """
        
        results = self.execute_query(query)
        for row in results:
            print(f"  {row[1]:<20} | {row[2]:<10} | I:{row[3]} U:{row[4]} D:{row[5]}")
    
    def check_index_usage(self):
        """检查索引使用情况"""
        print("\n🔍 索引使用统计:")
        print("-" * 50)
        
        query = """
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_tup_read,
            idx_tup_fetch,
            idx_scan
        FROM pg_stat_user_indexes
        WHERE idx_scan < 10  -- 使用次数少于10的索引
        ORDER BY idx_scan ASC;
        """
        
        results = self.execute_query(query)
        if results:
            print("⚠️  使用率较低的索引:")
            for row in results:
                print(f"  {row[1]}.{row[2]} - 扫描次数: {row[5]}")
        else:
            print("✅ 所有索引使用率良好")
    
    def check_slow_queries(self):
        """检查慢查询"""
        print("\n⏱️  查询性能统计:")
        print("-" * 50)
        
        # 检查pg_stat_statements是否存在
        check_extension = """
        SELECT EXISTS (
            SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
        );
        """
        
        has_extension = self.execute_query(check_extension)[0][0]
        
        if has_extension:
            query = """
            SELECT 
                query,
                calls,
                mean_time,
                total_time
            FROM pg_stat_statements
            WHERE mean_time > 100  -- 平均执行时间超过100ms
            ORDER BY mean_time DESC
            LIMIT 5;
            """
            results = self.execute_query(query)
            if results:
                for row in results:
                    print(f"  查询: {row[0][:50]}...")
                    print(f"    调用次数: {row[1]}, 平均时间: {row[2]:.2f}ms")
            else:
                print("✅ 没有发现慢查询")
        else:
            print("ℹ️  pg_stat_statements 扩展未安装，无法检查慢查询")
    
    def check_data_consistency(self):
        """检查数据一致性"""
        print("\n🔧 数据一致性检查:")
        print("-" * 50)
        
        checks = [
            {
                'name': 'remaining_supply 为负值',
                'query': 'SELECT COUNT(*) FROM assets WHERE remaining_supply < 0',
                'expected': 0
            },
            {
                'name': 'remaining_supply 超过 token_supply',
                'query': 'SELECT COUNT(*) FROM assets WHERE remaining_supply > token_supply',
                'expected': 0
            },
            {
                'name': '交易金额为负值',
                'query': 'SELECT COUNT(*) FROM trades WHERE amount <= 0 OR price < 0',
                'expected': 0
            },
            {
                'name': '孤立的佣金记录',
                'query': '''SELECT COUNT(*) FROM commission_records cr 
                           LEFT JOIN trades t ON cr.transaction_id = t.id 
                           WHERE t.id IS NULL''',
                'expected': 0
            },
            {
                'name': '无效的资产状态',
                'query': 'SELECT COUNT(*) FROM assets WHERE status NOT IN (1,2,3,4,5,6,7,8)',
                'expected': 0
            }
        ]
        
        for check in checks:
            result = self.execute_query(check['query'])[0][0]
            status = "✅" if result == check['expected'] else "❌"
            print(f"  {status} {check['name']}: {result}")
    
    def check_recent_activity(self):
        """检查最近活动"""
        print("\n📈 最近活动统计:")
        print("-" * 50)
        
        # 最近24小时的活动
        yesterday = datetime.now() - timedelta(days=1)
        
        queries = [
            ('新增资产', 'SELECT COUNT(*) FROM assets WHERE created_at >= %s', (yesterday,)),
            ('新增交易', 'SELECT COUNT(*) FROM trades WHERE created_at >= %s', (yesterday,)),
            ('完成交易', 'SELECT COUNT(*) FROM trades WHERE status = \'completed\' AND created_at >= %s', (yesterday,)),
            ('新增用户', 'SELECT COUNT(*) FROM users WHERE created_at >= %s', (yesterday,)),
        ]
        
        for name, query, params in queries:
            result = self.execute_query(query, params)[0][0]
            print(f"  {name} (24h): {result}")
    
    def check_database_locks(self):
        """检查数据库锁"""
        print("\n🔒 数据库锁状态:")
        print("-" * 50)
        
        query = """
        SELECT 
            pg_class.relname,
            pg_locks.locktype,
            pg_locks.mode,
            pg_locks.granted
        FROM pg_locks
        JOIN pg_class ON pg_locks.relation = pg_class.oid
        WHERE NOT pg_locks.granted;
        """
        
        results = self.execute_query(query)
        if results:
            print("⚠️  发现未授予的锁:")
            for row in results:
                print(f"  表: {row[0]}, 锁类型: {row[1]}, 模式: {row[2]}")
        else:
            print("✅ 没有发现阻塞的锁")
    
    def generate_optimization_suggestions(self):
        """生成优化建议"""
        print("\n💡 优化建议:")
        print("-" * 50)
        
        suggestions = []
        
        # 检查缺失的索引
        missing_indexes = """
        SELECT 
            schemaname, tablename, attname, n_distinct, correlation
        FROM pg_stats 
        WHERE schemaname = 'public' 
        AND n_distinct > 100 
        AND tablename IN ('assets', 'trades', 'users', 'commission_records')
        AND attname NOT IN (
            SELECT column_name 
            FROM information_schema.statistics 
            WHERE table_schema = 'public'
        );
        """
        
        # 检查表膨胀
        bloat_query = """
        SELECT 
            schemaname, tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """
        
        results = self.execute_query(bloat_query)
        large_tables = [row for row in results if 'MB' in row[2] or 'GB' in row[2]]
        
        if large_tables:
            suggestions.append("考虑对大表进行VACUUM和REINDEX操作")
        
        suggestions.extend([
            "定期执行ANALYZE更新表统计信息",
            "监控慢查询日志",
            "考虑分区大表以提高查询性能",
            "定期备份数据库",
            "监控磁盘空间使用情况"
        ])
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    
    def run_full_check(self):
        """运行完整的健康检查"""
        print("🏥 RWA-HUB 5.0 数据库健康检查报告")
        print("=" * 60)
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        if not self.connect():
            return
        
        try:
            self.check_table_sizes()
            self.check_index_usage()
            self.check_slow_queries()
            self.check_data_consistency()
            self.check_recent_activity()
            self.check_database_locks()
            self.generate_optimization_suggestions()
            
        except Exception as e:
            print(f"❌ 检查过程中出现错误: {e}")
        finally:
            self.disconnect()
        
        print("\n" + "=" * 60)
        print("✅ 健康检查完成")

def main():
    """主函数"""
    checker = DatabaseHealthChecker(DB_CONFIG)
    checker.run_full_check()

if __name__ == "__main__":
    main()
