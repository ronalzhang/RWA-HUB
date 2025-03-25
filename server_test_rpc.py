#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import time
import sys

# 测试节点列表
rpc_endpoints = [
    'https://api.mainnet-beta.solana.com',
    'https://solana.blockpi.network/v1/rpc/public',
    'https://api.testnet.solana.com',
    'https://api.devnet.solana.com',
    'https://rpc.ankr.com/solana',
    'https://free.rpcpool.com',
    'https://solana-mainnet.rpc.extrnode.com',
    'https://solana-api.projectserum.com',
]

print('=== 服务器Solana RPC节点连接测试 ===')
results = []

for endpoint in rpc_endpoints:
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'getSlot',
        'params': []
    }
    headers = {'Content-Type': 'application/json'}
    
    print(f'测试节点: {endpoint}')
    start_time = time.time()
    
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                print(f'  ✅ 成功 (响应时间: {response_time:.3f}秒)')
                results.append({
                    'endpoint': endpoint,
                    'success': True,
                    'response_time': response_time
                })
            else:
                print(f'  ❌ RPC方法错误: {result.get("error", {}).get("message", "未知错误")}')
                results.append({
                    'endpoint': endpoint,
                    'success': False,
                    'response_time': response_time
                })
        else:
            print(f'  ❌ HTTP错误: {response.status_code}')
            results.append({
                'endpoint': endpoint,
                'success': False,
                'response_time': response_time
            })
    except requests.exceptions.Timeout:
        print('  ❌ 连接超时')
        results.append({
            'endpoint': endpoint,
            'success': False,
            'response_time': 10
        })
    except Exception as e:
        print(f'  ❌ 连接错误: {str(e)}')
        results.append({
            'endpoint': endpoint,
            'success': False,
            'response_time': time.time() - start_time
        })
    
    # 短暂暂停
    time.sleep(1)

# 按成功和响应时间排序
sorted_results = sorted(results, key=lambda x: (not x['success'], x['response_time']))

print('\n=== 推荐节点顺序 (JS格式) ===')
print('const rpcEndpoints = [')
# 先列出成功的节点
for result in sorted_results:
    if result['success']:
        print(f'    \'{result["endpoint"]}\',')
# 再列出失败的节点
for result in sorted_results:
    if not result['success']:
        print(f'    \'{result["endpoint"]}\',')
print('];') 