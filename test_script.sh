#!/bin/bash

# 创建Python测试脚本
cat > test_rpc_nodes.py << 'EOL'
#!/usr/bin/env python3
import requests
import time
import json

# 测试的RPC节点列表
rpc_endpoints = [
    "https://api.mainnet-beta.solana.com",
    "https://rpc.ankr.com/solana", 
    "https://solana.blockpi.network/v1/rpc/public",
    "https://solana-api.tt-prod.net",
    "https://solana.rpc.extrnode.com",
    "https://free.rpcpool.com",
    "https://sol.getblock.io/mainnet",
    "https://api-eu.getblock.io/mainnet",
    "https://api.devnet.solana.com",
    "https://solana.public-rpc.com"
]

results = []

# 测试每个节点
for endpoint in rpc_endpoints:
    print(f"测试节点: {endpoint}")
    
    # 使用getSlot方法，这个方法更基础
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSlot",
        "params": []
    }
    
    start_time = time.time()
    success = False
    error_msg = ""
    
    try:
        # 发送请求，设置5秒超时
        response = requests.post(endpoint, json=payload, timeout=5)
        
        # 验证响应
        if response.status_code == 200:
            response_data = response.json()
            if "result" in response_data:
                success = True
            else:
                error_msg = f"无有效结果: {response_data.get('error', '未知错误')}"
        else:
            error_msg = f"HTTP错误: {response.status_code}"
    
    except requests.exceptions.Timeout:
        error_msg = "连接超时"
    except requests.exceptions.ConnectionError:
        error_msg = "连接错误"
    except Exception as e:
        error_msg = f"异常: {str(e)}"
    
    # 计算响应时间
    response_time = time.time() - start_time
    
    # 记录结果
    results.append({
        "endpoint": endpoint,
        "success": success,
        "response_time": response_time,
        "error": error_msg
    })
    
    print(f"  结果: {'成功' if success else '失败'}, 响应时间: {response_time:.3f}秒, 错误: {error_msg}")
    
    # 短暂暂停，避免过多请求
    time.sleep(1)

# 按成功率和响应时间排序
sorted_results = sorted(results, key=lambda x: (not x["success"], x["response_time"]))

print("\n节点连接性能排名:")
for i, result in enumerate(sorted_results):
    status = "成功" if result["success"] else "失败"
    print(f"{i+1}. {result['endpoint']} - {status}, 响应时间: {result['response_time']:.3f}秒")

# 输出JavaScript数组格式的排序后节点列表
js_array = "[\n"
for result in sorted_results:
    if result["success"]:  # 只包含成功的节点
        js_array += f"    \"{result['endpoint']}\",\n"
js_array += "]"

print("\n排序后的JavaScript节点数组:")
print(js_array)
EOL

# 上传脚本到服务器
scp -i vincent.pem test_rpc_nodes.py root@47.236.39.134:/root/RWA-HUB/test_rpc_nodes.py

# 在服务器上运行脚本
ssh -i vincent.pem root@47.236.39.134 "cd /root/RWA-HUB && chmod +x test_rpc_nodes.py && python3 test_rpc_nodes.py" 