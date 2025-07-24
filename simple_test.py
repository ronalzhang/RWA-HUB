#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# 简单的数据库查询测试，不需要创建完整的Flask应用
import psycopg2

def test_direct_query():
    """直接查询数据库"""
    try:
        # 连接数据库
        conn = psycopg2.connect(
            host="localhost",
            database="rwa_hub",
            user="rwa_hub_user",
            password="password"
        )
        cursor = conn.cursor()
        
        wallet_address = '8cU6PAtRTRgfyJu48qfz2hQP5aMGwooxqrCZtyB6UcYP'
        print(f'测试钱包地址: {wallet_address}')
        
        # 查询交易记录
        cursor.execute("""
            SELECT id, asset_id, trader_address, trade_type, status, amount, price, created_at
            FROM trades 
            WHERE trader_address = %s
            ORDER BY created_at DESC
        """, (wallet_address,))
        
        trades = cursor.fetchall()
        print(f'\n找到交易记录: {len(trades)} 条')
        
        for trade in trades:
            trade_id, asset_id, trader_addr, trade_type, status, amount, price, created_at = trade
            print(f'- 交易ID: {trade_id}, 资产ID: {asset_id}, 类型: {trade_type}, 状态: {status}, 数量: {amount}, 时间: {created_at}')
        
        # 查询这些资产的详情
        if trades:
            asset_ids = [str(trade[1]) for trade in trades]  # 获取所有asset_id
            placeholders = ', '.join(['%s'] * len(asset_ids))
            
            cursor.execute(f"""
                SELECT id, name, token_symbol, token_price, token_supply
                FROM assets 
                WHERE id IN ({placeholders})
            """, asset_ids)
            
            assets = cursor.fetchall()
            print(f'\n对应的资产信息: {len(assets)} 个')
            
            for asset in assets:
                asset_id, name, token_symbol, token_price, token_supply = asset
                print(f'- 资产ID: {asset_id}, 名称: {name}, 符号: {token_symbol}, 价格: {token_price}')
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f'数据库查询错误: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_direct_query()