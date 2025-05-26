#!/usr/bin/env python3
"""
服务器端支付配置测试脚本
用于检查数据库中的配置和API返回结果
"""

import sys
import os
import json
import requests
from datetime import datetime

# 添加项目路径到Python路径
sys.path.insert(0, '/root/RWA-HUB')

def test_database_config():
    """测试数据库中的配置"""
    print("=" * 50)
    print("测试数据库配置")
    print("=" * 50)
    
    try:
        from app import create_app
        from app.models.admin import SystemConfig
        
        app = create_app()
        with app.app_context():
            # 检查关键配置
            configs_to_check = [
                'PLATFORM_FEE_ADDRESS',
                'ASSET_CREATION_FEE_ADDRESS', 
                'ASSET_CREATION_FEE_AMOUNT',
                'PLATFORM_FEE_BASIS_POINTS'
            ]
            
            print("数据库中的配置:")
            for config_key in configs_to_check:
                value = SystemConfig.get_value(config_key, 'NOT_SET')
                print(f"  {config_key}: {value}")
                
            return True
    except Exception as e:
        print(f"数据库配置测试失败: {e}")
        return False

def test_api_response():
    """测试API响应"""
    print("\n" + "=" * 50)
    print("测试API响应")
    print("=" * 50)
    
    try:
        from app import create_app
        from app.routes.service import get_payment_settings
        
        app = create_app()
        with app.app_context():
            with app.test_request_context():
                result = get_payment_settings()
                response_data = result.get_json()
                
                print("API返回结果:")
                print(json.dumps(response_data, indent=2, ensure_ascii=False))
                
                return response_data
    except Exception as e:
        print(f"API测试失败: {e}")
        return None

def test_live_api():
    """测试实际的HTTP API"""
    print("\n" + "=" * 50)
    print("测试实际HTTP API")
    print("=" * 50)
    
    # 测试多个URL
    urls_to_test = [
        'http://localhost:9000/api/service/config/payment_settings',
        'https://rwa-hub.com/api/service/config/payment_settings'
    ]
    
    for url in urls_to_test:
        try:
            print(f"\n请求URL: {url}")
            
            response = requests.get(url, timeout=10)
            print(f"HTTP状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("HTTP API返回结果:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return data
            else:
                print(f"HTTP请求失败: {response.text}")
                
        except Exception as e:
            print(f"HTTP API测试失败 ({url}): {e}")
            
    return None

def test_production_api():
    """专门测试生产环境API"""
    print("\n" + "=" * 50)
    print("测试生产环境API")
    print("=" * 50)
    
    try:
        url = 'https://rwa-hub.com/api/service/config/payment_settings'
        print(f"请求生产环境URL: {url}")
        
        headers = {
            'User-Agent': 'RWA-Hub-Test-Script/1.0',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        print(f"HTTP状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("生产环境API返回结果:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 检查关键字段
            expected_address = 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4'
            platform_address = data.get('platform_fee_address', 'NOT_FOUND')
            creation_address = data.get('asset_creation_fee_address', 'NOT_FOUND')
            
            print(f"\n配置检查:")
            print(f"期望地址: {expected_address}")
            print(f"平台收款地址: {platform_address}")
            print(f"资产创建收款地址: {creation_address}")
            
            if platform_address == expected_address or creation_address == expected_address:
                print("✅ 生产环境配置正确!")
            else:
                print("❌ 生产环境配置不匹配!")
                
            return data
        else:
            print(f"生产环境API请求失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"生产环境API测试失败: {e}")
        return None

def update_database_config():
    """更新数据库配置为正确的地址"""
    print("\n" + "=" * 50)
    print("更新数据库配置")
    print("=" * 50)
    
    try:
        from app import create_app
        from app.models.admin import SystemConfig
        
        app = create_app()
        with app.app_context():
            # 设置正确的配置
            target_address = 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4'
            
            configs_to_update = {
                'PLATFORM_FEE_ADDRESS': target_address,
                'ASSET_CREATION_FEE_ADDRESS': target_address,
                'ASSET_CREATION_FEE_AMOUNT': '0.02',
                'PLATFORM_FEE_BASIS_POINTS': '350'
            }
            
            print("更新配置:")
            for key, value in configs_to_update.items():
                SystemConfig.set_value(key, value, f'Updated by test script at {datetime.now()}')
                print(f"  {key}: {value}")
                
            print("配置更新完成!")
            return True
            
    except Exception as e:
        print(f"更新配置失败: {e}")
        return False

def main():
    """主函数"""
    print(f"服务器支付配置测试 - {datetime.now()}")
    print("Python路径:", sys.path[0])
    print("工作目录:", os.getcwd())
    
    # 首先测试生产环境API
    print("\n🌐 测试生产环境...")
    production_result = test_production_api()
    
    # 如果在服务器环境中运行，则进行本地测试
    if os.path.exists('/root/RWA-HUB'):
        print("\n🖥️  检测到服务器环境，进行本地测试...")
        
        # 1. 测试数据库配置
        db_success = test_database_config()
        
        # 2. 如果数据库配置不正确，尝试更新
        if not db_success:
            print("\n数据库配置测试失败，尝试更新配置...")
            update_database_config()
            # 重新测试
            test_database_config()
        
        # 3. 测试API响应
        api_result = test_api_response()
        
        # 4. 测试本地HTTP API
        http_result = test_live_api()
        
        # 5. 总结本地测试
        print("\n" + "=" * 50)
        print("本地测试总结")
        print("=" * 50)
        
        if api_result:
            expected_address = 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4'
            actual_address = api_result.get('platform_fee_address', 'NOT_FOUND')
            actual_creation_address = api_result.get('asset_creation_fee_address', 'NOT_FOUND')
            
            print(f"期望的收款地址: {expected_address}")
            print(f"API返回的平台收款地址: {actual_address}")
            print(f"API返回的资产创建收款地址: {actual_creation_address}")
            
            if actual_address == expected_address or actual_creation_address == expected_address:
                print("✅ 本地配置正确!")
            else:
                print("❌ 本地配置不匹配!")
        else:
            print("❌ 本地API测试失败!")
    else:
        print("\n💻 非服务器环境，跳过本地测试")
    
    # 最终总结
    print("\n" + "=" * 60)
    print("最终测试总结")
    print("=" * 60)
    
    if production_result:
        print("✅ 生产环境API测试成功")
    else:
        print("❌ 生产环境API测试失败")
        
    print("\n建议:")
    if not production_result:
        print("1. 检查服务器是否正常运行")
        print("2. 检查API路由是否正确配置")
        print("3. 检查数据库配置是否正确同步")

if __name__ == '__main__':
    main() 