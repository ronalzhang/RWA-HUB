#!/usr/bin/env python3
"""
诊断模板部署问题
检查服务器上的模板文件是否正确包含智能合约部署脚本引用
"""

import requests
import re
from urllib.parse import urljoin

def check_page_scripts(url, expected_scripts):
    """检查页面中的脚本引用"""
    print(f"\n🔍 检查页面: {url}")
    
    try:
        # 禁用SSL警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.get(url, verify=False, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ 页面访问失败: {response.status_code}")
            return False
        
        content = response.text
        print(f"✅ 页面访问成功，内容长度: {len(content)} 字符")
        
        # 查找所有script标签
        script_pattern = r'<script[^>]*src=["\']([^"\']*)["\'][^>]*></script>'
        scripts = re.findall(script_pattern, content, re.IGNORECASE)
        
        print(f"\n📋 找到的脚本引用 ({len(scripts)} 个):")
        for i, script in enumerate(scripts, 1):
            print(f"  {i}. {script}")
        
        # 检查期望的脚本
        print(f"\n🎯 检查期望的脚本:")
        missing_scripts = []
        found_scripts = []
        
        for expected in expected_scripts:
            found = False
            for script in scripts:
                if expected in script:
                    found = True
                    found_scripts.append(expected)
                    print(f"  ✅ {expected}: 找到")
                    break
            
            if not found:
                missing_scripts.append(expected)
                print(f"  ❌ {expected}: 缺失")
        
        # 检查智能合约部署脚本的具体情况
        if 'smart_contract_deployment.js' in missing_scripts:
            print(f"\n🔍 详细检查智能合约部署脚本引用:")
            
            # 搜索可能的引用模式
            patterns = [
                r'smart_contract_deployment\.js',
                r'smart_contract_deployment',
                r'deploySmartContract',
                r'SmartContractDeployment'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    print(f"  🔍 找到模式 '{pattern}': {len(matches)} 次")
                else:
                    print(f"  ❌ 未找到模式 '{pattern}'")
        
        return len(missing_scripts) == 0
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def check_static_file_accessibility():
    """检查静态文件的可访问性"""
    print(f"\n🔍 检查静态文件可访问性:")
    
    base_url = "https://rwa-hub.com"
    static_files = [
        "/static/js/smart_contract_deployment.js",
        "/static/js/wallet.js",
        "/static/js/handle_buy.js"
    ]
    
    # 禁用SSL警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    all_accessible = True
    
    for file_path in static_files:
        try:
            url = urljoin(base_url, file_path)
            response = requests.get(url, verify=False, timeout=10)
            
            if response.status_code == 200:
                size = len(response.content)
                print(f"  ✅ {file_path}: 可访问 ({size} 字节)")
                
                # 对于智能合约部署脚本，检查关键函数
                if 'smart_contract_deployment.js' in file_path:
                    content = response.text
                    key_functions = ['deploySmartContract', 'SmartContractDeployment', 'CompletePurchaseFlow']
                    
                    print(f"    🔍 检查关键函数:")
                    for func in key_functions:
                        if func in content:
                            print(f"      ✅ {func}: 存在")
                        else:
                            print(f"      ❌ {func}: 缺失")
                            
            else:
                print(f"  ❌ {file_path}: 不可访问 ({response.status_code})")
                all_accessible = False
                
        except Exception as e:
            print(f"  ❌ {file_path}: 检查失败 - {e}")
            all_accessible = False
    
    return all_accessible

def check_template_deployment_status():
    """检查模板部署状态"""
    print(f"\n🔍 检查模板部署状态:")
    
    # 检查资产详情页面
    detail_success = check_page_scripts(
        "https://rwa-hub.com/assets/RH-106046",
        ["wallet.js", "handle_buy.js", "smart_contract_deployment.js"]
    )
    
    # 检查静态文件
    static_success = check_static_file_accessibility()
    
    return detail_success, static_success

def main():
    """主函数"""
    print("🔧 模板部署诊断工具")
    print("=" * 60)
    
    detail_success, static_success = check_template_deployment_status()
    
    print(f"\n" + "=" * 60)
    print("📊 诊断结果总结")
    
    print(f"资产详情页面脚本引用: {'✅ 正常' if detail_success else '❌ 异常'}")
    print(f"静态文件可访问性: {'✅ 正常' if static_success else '❌ 异常'}")
    
    if detail_success and static_success:
        print("\n🎉 所有检查通过！智能合约部署功能应该正常工作")
    else:
        print("\n⚠️  发现问题，需要进一步修复")
        
        if not detail_success:
            print("\n🔧 修复建议:")
            print("1. 检查服务器上的模板文件是否正确部署")
            print("2. 确认应用是否正确重启")
            print("3. 检查模板缓存是否需要清除")
        
        if not static_success:
            print("\n🔧 静态文件修复建议:")
            print("1. 重新上传智能合约部署脚本")
            print("2. 检查服务器文件权限")
            print("3. 确认静态文件路径配置")
    
    return 0 if (detail_success and static_success) else 1

if __name__ == "__main__":
    exit(main())