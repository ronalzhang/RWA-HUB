#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试真实网络模式下的自动上链功能
临时降低SOL余额阈值以适应当前余额
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.extensions import db
from app import create_app
from app.models.asset import Asset, AssetStatus
from app.blockchain.solana import SolanaClient
import time

def test_auto_onchain():
    """测试自动上链功能"""
    
    print("🚀 开始测试真实网络模式下的自动上链功能...")
    
    app = create_app()
    with app.app_context():
        
        # 1. 检查当前SOL余额
        print("\n📍 第一步：检查服务钱包状态")
        client = SolanaClient()
        balance = client.get_balance()
        print(f"💰 当前SOL余额: {balance} SOL")
        
        if balance < 0.005:  # 至少需要0.005 SOL用于基本交易
            print("❌ SOL余额过低，无法进行任何链上操作")
            return
        
        # 2. 找一个状态为PENDING的资产进行测试
        print("\n📍 第二步：查找测试资产")
        test_asset = Asset.query.filter_by(status=AssetStatus.PENDING.value).first()
        
        if not test_asset:
            print("❌ 未找到状态为PENDING的资产")
            return
            
        print(f"✅ 找到测试资产: ID={test_asset.id}, 名称={test_asset.name}")
        print(f"   当前状态: {test_asset.status} (PENDING)")
        print(f"   支付确认: {test_asset.payment_confirmed}")
        
        # 3. 更新资产状态以触发自动上链
        print("\n📍 第三步：触发自动上链条件")
        
        # 首先确认支付状态
        if not test_asset.payment_confirmed:
            print("   设置支付确认状态...")
            test_asset.payment_confirmed = True
            
        # 设置为CONFIRMED状态以触发自动上链
        print("   更新资产状态为CONFIRMED...")
        test_asset.status = AssetStatus.CONFIRMED.value
        
        # 保存更改
        db.session.commit()
        print(f"✅ 资产状态已更新: ID={test_asset.id}, 状态={test_asset.status} (CONFIRMED)")
        
        # 4. 等待自动上链系统处理
        print("\n📍 第四步：监控自动上链过程")
        print("⏳ 等待自动上链监控系统处理...")
        print("   (自动监控系统每5分钟运行一次)")
        
        # 监控状态变化（最多等待10分钟）
        max_wait_time = 600  # 10分钟
        check_interval = 30   # 每30秒检查一次
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            time.sleep(check_interval)
            elapsed_time += check_interval
            
            # 刷新资产状态
            db.session.refresh(test_asset)
            
            print(f"   [{elapsed_time//60:02d}:{elapsed_time%60:02d}] 检查状态...")
            print(f"   当前状态: {test_asset.status}")
            print(f"   Token地址: {test_asset.token_address}")
            
            if test_asset.status == AssetStatus.ON_CHAIN.value:
                print("🎉 自动上链成功完成！")
                break
            elif test_asset.status == AssetStatus.DEPLOYMENT_FAILED.value:
                print("❌ 自动上链失败")
                break
                
        # 5. 输出最终结果
        print("\n📍 第五步：测试结果总结")
        db.session.refresh(test_asset)
        
        print(f"资产ID: {test_asset.id}")
        print(f"最终状态: {test_asset.status}")
        print(f"Token地址: {test_asset.token_address}")
        print(f"支付确认: {test_asset.payment_confirmed}")
        
        # 检查最终SOL余额
        final_balance = client.get_balance()
        balance_change = balance - final_balance if final_balance else 0
        print(f"初始SOL余额: {balance} SOL")
        print(f"最终SOL余额: {final_balance} SOL")
        print(f"消耗SOL: {balance_change:.9f} SOL")
        
        if test_asset.status == AssetStatus.ON_CHAIN.value:
            print("\n🎉 测试成功：真实网络自动上链功能正常工作！")
            if test_asset.token_address:
                print(f"🔗 Solana Explorer: https://explorer.solana.com/address/{test_asset.token_address}")
        else:
            print("\n⚠️  测试结果：自动上链未完成或失败")
            
if __name__ == "__main__":
    test_auto_onchain() 