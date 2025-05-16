from flask import Blueprint, request, jsonify, current_app, g, Response
import time
import json
import logging
import requests
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils.solana_logger import log_transaction, log_api_call, log_error, init_solana_logger
from app.utils.solana_log_reader import SolanaLogReader
import os
from datetime import datetime, timedelta, timezone
from threading import Lock
import uuid
import traceback

# 创建日志器
logger = logging.getLogger('solana_api')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# 初始化日志系统
solana_loggers = init_solana_logger()

# 创建Blueprint
solana_api = Blueprint('solana_api', __name__, url_prefix='/api/solana')

# Solana RPC节点列表
RPC_NODES = [
    # 官方节点
    "https://api.mainnet-beta.solana.com",
    # Project Serum节点 (CDN可能在中国访问更快)
    "https://solana-api.projectserum.com",
    # GenesysGo节点
    "https://ssc-dao.genesysgo.net",
    # Ankr节点
    "https://rpc.ankr.com/solana",
    # Alchemy演示节点
    "https://solana-mainnet.g.alchemy.com/v2/demo",
    "https://solana-mainnet.g.alchemy.com/v2/VvBRX5GaJA5VC5M1F681uL-3ivk3wGt2",
    "https://mainnet.rpcpool.com"
]

# 节点状态缓存
NODE_STATUS = {
    node: {
        "available": True,
        "last_check": 0,
        "latency": 999,
        "consecutive_failures": 0
    } for node in RPC_NODES
}

# 使用线程池执行并发请求
executor = ThreadPoolExecutor(max_workers=5)

# 实例化日志读取器
log_reader = SolanaLogReader()

def check_node_health(node_url):
    """检查RPC节点健康状态"""
    try:
        start_time = time.time()
        response = requests.post(
            node_url,
            json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
            headers={"Content-Type": "application/json"},
            timeout=3
        )
        latency = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            if result.get("result") == "ok":
                NODE_STATUS[node_url]["available"] = True
                NODE_STATUS[node_url]["latency"] = latency
                NODE_STATUS[node_url]["consecutive_failures"] = 0
                logger.info(f"节点 {node_url} 健康检查通过, 延迟: {latency:.3f}s")
                return True, latency
            else:
                NODE_STATUS[node_url]["consecutive_failures"] += 1
                logger.warning(f"节点 {node_url} 健康检查返回非ok状态: {result.get('result')}")
        else:
            NODE_STATUS[node_url]["consecutive_failures"] += 1
            logger.warning(f"节点 {node_url} 健康检查HTTP状态码异常: {response.status_code}")
        
        # 如果连续失败超过3次，标记为不可用
        if NODE_STATUS[node_url]["consecutive_failures"] >= 3:
            NODE_STATUS[node_url]["available"] = False
        
        return False, 999
    except Exception as e:
        NODE_STATUS[node_url]["consecutive_failures"] += 1
        if NODE_STATUS[node_url]["consecutive_failures"] >= 3:
            NODE_STATUS[node_url]["available"] = False
        logger.error(f"节点 {node_url} 健康检查异常: {str(e)}")
        return False, 999

def get_best_node():
    """获取最佳RPC节点"""
    current_time = time.time()
    
    # 每60秒检查一次所有节点的健康状态
    check_all = False
    for node_url in RPC_NODES:
        if current_time - NODE_STATUS[node_url]["last_check"] > 60:
            check_all = True
            break
    
    if check_all:
        logger.info("开始检查所有节点健康状态")
        futures = {executor.submit(check_node_health, node_url): node_url for node_url in RPC_NODES}
        for future in as_completed(futures):
            node_url = futures[future]
            try:
                is_healthy, latency = future.result()
                NODE_STATUS[node_url]["last_check"] = current_time
            except Exception as e:
                logger.error(f"检查节点 {node_url} 时发生异常: {str(e)}")
    
    # 选择可用且延迟最低的节点
    available_nodes = [(node, info) for node, info in NODE_STATUS.items() if info["available"]]
    if not available_nodes:
        # 如果没有可用节点，重置所有节点状态并返回第一个
        logger.warning("没有可用节点，重置所有节点状态")
        for node in RPC_NODES:
            NODE_STATUS[node]["available"] = True
            NODE_STATUS[node]["consecutive_failures"] = 0
        return RPC_NODES[0]
    
    # 按延迟排序
    available_nodes.sort(key=lambda x: x[1]["latency"])
    best_node = available_nodes[0][0]
    logger.info(f"选择最佳节点: {best_node}, 延迟: {available_nodes[0][1]['latency']:.3f}s")
    return best_node

def make_rpc_request(method, params=None, node_url=None, retry=2):
    """
    向Solana RPC节点发送请求
    
    Args:
        method: RPC方法名
        params: 请求参数
        node_url: 指定节点URL，如不指定则自动选择
        retry: 重试次数
    
    Returns:
        响应结果
    """
    if params is None:
        params = []
    
    if node_url is None:
        node_url = get_best_node()
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    logger.info(f"向节点 {node_url} 发送 {method} 请求")
    
    try:
        response = requests.post(node_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                return {"success": True, "result": result["result"]}
            elif "error" in result:
                error_msg = result["error"].get("message", "未知错误")
                logger.error(f"RPC请求返回错误: {error_msg}")
                
                # 对于特定错误，标记节点为不可用
                if "429" in str(error_msg) or "timeout" in str(error_msg).lower():
                    NODE_STATUS[node_url]["consecutive_failures"] += 1
                    if NODE_STATUS[node_url]["consecutive_failures"] >= 3:
                        NODE_STATUS[node_url]["available"] = False
                
                if retry > 0:
                    # 使用不同节点重试
                    next_node = None
                    for n in RPC_NODES:
                        if n != node_url and NODE_STATUS[n]["available"]:
                            next_node = n
                            break
                    
                    if next_node:
                        logger.info(f"在节点 {next_node} 上重试请求")
                        return make_rpc_request(method, params, next_node, retry - 1)
                
                return {"success": False, "error": error_msg}
        else:
            logger.error(f"RPC请求HTTP状态码异常: {response.status_code}")
            if retry > 0:
                # 标记当前节点故障并重试
                NODE_STATUS[node_url]["consecutive_failures"] += 1
                if NODE_STATUS[node_url]["consecutive_failures"] >= 3:
                    NODE_STATUS[node_url]["available"] = False
                
                next_node = None
                for n in RPC_NODES:
                    if n != node_url and NODE_STATUS[n]["available"]:
                        next_node = n
                        break
                
                if next_node:
                    logger.info(f"在节点 {next_node} 上重试请求")
                    return make_rpc_request(method, params, next_node, retry - 1)
            
            return {"success": False, "error": f"HTTP错误: {response.status_code}"}
    except Exception as e:
        logger.exception(f"RPC请求发生异常: {str(e)}")
        
        # 标记当前节点故障
        NODE_STATUS[node_url]["consecutive_failures"] += 1
        if NODE_STATUS[node_url]["consecutive_failures"] >= 3:
            NODE_STATUS[node_url]["available"] = False
        
        if retry > 0:
            # 使用不同节点重试
            next_node = None
            for n in RPC_NODES:
                if n != node_url and NODE_STATUS[n]["available"]:
                    next_node = n
                    break
            
            if next_node:
                logger.info(f"在节点 {next_node} 上重试请求")
                return make_rpc_request(method, params, next_node, retry - 1)
        
        return {"success": False, "error": f"请求异常: {str(e)}"}

@solana_api.before_request
def before_request():
    """记录请求开始时间"""
    g.start_time = time.time()

@solana_api.after_request
def after_request(response):
    """记录API调用"""
    if hasattr(g, 'start_time'):
        response_time = time.time() - g.start_time
        
        # 尝试解析响应数据
        response_data = None
        if response.content_type == 'application/json':
            try:
                response_data = json.loads(response.data.decode('utf-8'))
            except:
                pass
        
        # 记录API调用
        log_api_call({
            'endpoint': request.path,
            'status_code': response.status_code,
            'response_time': response_time,
            'method': request.method,
            'params': dict(request.args),
            'client_ip': request.remote_addr,
            'response_status': 'success' if response.status_code < 400 else 'error',
            'response_data': response_data
        })
    
    return response

@solana_api.route('/health', methods=['GET'])
def health_check():
    """API健康检查"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@solana_api.route('/submit_transaction', methods=['POST'])
def submit_transaction():
    """
    提交已签名的Solana交易
    
    请求体:
    {
        "serialized_transaction": "BASE64_ENCODED_TRANSACTION",
        "skip_preflight": false,  // 可选
        "from_address": "",       // 可选，用于日志记录
        "to_address": "",         // 可选，用于日志记录
        "amount": 0,              // 可选，用于日志记录
        "token": ""               // 可选，用于日志记录
    }
    """
    try:
        data = request.json
        if not data or 'serialized_transaction' not in data:
            return jsonify({"success": False, "error": "缺少必要参数"}), 400
        
        serialized_transaction = data['serialized_transaction']
        skip_preflight = data.get('skip_preflight', False)
        
        # 获取可选的日志参数
        from_address = data.get('from_address', 'unknown')
        to_address = data.get('to_address', 'unknown')
        amount = data.get('amount', 0)
        token = data.get('token', 'UNKNOWN')
        
        # 发送交易
        result = make_rpc_request(
            "sendTransaction",
            [
                serialized_transaction,
                {
                    "skipPreflight": skip_preflight,
                    "preflightCommitment": "confirmed",
                    "encoding": "base64"
                }
            ]
        )
        
        if result["success"]:
            signature = result["result"]
            logger.info(f"交易提交成功, 签名: {signature}")
            
            # 记录交易日志
            log_transaction({
                'transaction_id': signature,
                'wallet_address': from_address,
                'type': 'transfer',
                'amount': amount,
                'token': token,
                'status': "submitted",
                'block_number': None,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'to_address': to_address,
                'details': {
                    "skip_preflight": skip_preflight,
                    "remote_addr": request.remote_addr
                }
            })
            
            return jsonify({"success": True, "signature": signature})
        else:
            # 记录失败交易
            log_transaction({
                'transaction_id': "failed_submission",
                'wallet_address': from_address,
                'type': 'transfer',
                'amount': amount,
                'token': token,
                'status': "failed",
                'block_number': None,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'to_address': to_address,
                'details': {
                    "error": result["error"],
                    "remote_addr": request.remote_addr
                }
            })
            
            return jsonify({"success": False, "error": result["error"]}), 400
    except Exception as e:
        logger.exception(f"提交交易时发生异常: {str(e)}")
        
        # 记录错误
        log_error({
            'error_id': str(uuid.uuid4()),
            'level': "ERROR",
            'message': str(e),
            'component': "transaction_submission",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stack_trace': traceback.format_exc(),
            'details': {
                "from_address": data.get('from_address', 'unknown') if data else 'unknown',
                "remote_addr": request.remote_addr,
                "request_data": str(data) if data else 'none'
            }
        })
        
        return jsonify({"success": False, "error": str(e)}), 500

@solana_api.route('/check_transaction', methods=['GET'])
def check_transaction():
    """
    检查交易状态
    
    参数:
    - signature: 交易签名
    - from_address: 可选，发送地址（用于日志记录）
    - to_address: 可选，接收地址（用于日志记录）
    - amount: 可选，金额（用于日志记录）
    - token: 可选，代币符号（用于日志记录）
    """
    try:
        signature = request.args.get('signature')
        if not signature:
            return jsonify({"success": False, "error": "缺少交易签名参数"}), 400
        
        # 获取可选的日志参数
        from_address = request.args.get('from_address', 'unknown')
        to_address = request.args.get('to_address', 'unknown')
        amount = request.args.get('amount', 0)
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0
        token = request.args.get('token', 'UNKNOWN')
        
        # 获取交易状态
        result = make_rpc_request(
            "getSignatureStatuses",
            [[signature], {"searchTransactionHistory": True}]
        )
        
        if result["success"]:
            status_info = result["result"]["value"][0]
            
            if status_info is None:
                return jsonify({
                    "success": True, 
                    "confirmed": False,
                    "status": "not_found",
                    "message": "交易未找到或尚未处理"
                })
            
            confirmed = status_info.get("confirmationStatus") in ["confirmed", "finalized"]
            
            # 记录交易确认状态
            if confirmed:
                log_transaction({
                    'transaction_id': signature,
                    'wallet_address': from_address,
                    'type': 'transfer',
                    'amount': amount,
                    'token': token,
                    'status': "confirmed",
                    'block_number': status_info.get("slot"),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'to_address': to_address,
                    'details': {
                        "confirmation_status": status_info.get("confirmationStatus"),
                        "slot": status_info.get("slot"),
                        "confirmations": status_info.get("confirmations")
                    }
                })
            elif status_info.get("err"):
                # 交易出错
                log_transaction({
                    'transaction_id': signature,
                    'wallet_address': from_address,
                    'type': 'transfer',
                    'amount': amount,
                    'token': token,
                    'status': "failed",
                    'block_number': status_info.get("slot"),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'to_address': to_address,
                    'details': {
                        "error": str(status_info.get("err")),
                        "slot": status_info.get("slot")
                    }
                })
            
            return jsonify({
                "success": True,
                "confirmed": confirmed,
                "status": status_info.get("confirmationStatus", "unknown"),
                "slot": status_info.get("slot"),
                "confirmations": status_info.get("confirmations"),
                "error": status_info.get("err")
            })
        else:
            return jsonify({"success": False, "error": result["error"]}), 400
    except Exception as e:
        logger.exception(f"检查交易状态时发生异常: {str(e)}")
        
        # 记录错误
        log_error({
            'error_id': str(uuid.uuid4()),
            'level': "ERROR",
            'message': str(e),
            'component': "transaction_check",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stack_trace': traceback.format_exc(),
            'details': {
                "signature": request.args.get('signature', 'unknown'),
                "remote_addr": request.remote_addr
            }
        })
        
        return jsonify({"success": False, "error": str(e)}), 500

@solana_api.route('/get_token_accounts', methods=['GET'])
def get_token_accounts():
    """
    获取账户的代币账户信息
    
    参数:
    - owner: 账户公钥
    - mint: (可选) 代币Mint地址，指定时只返回该代币的账户
    """
    try:
        owner = request.args.get('owner')
        mint = request.args.get('mint')
        
        if not owner:
            return jsonify({"success": False, "error": "缺少owner参数"}), 400
        
        logger.info(f"获取代币账户 - 所有者: {owner}, 代币Mint: {mint}")
        
        # 构建请求参数
        params = [
            owner,
            {"encoding": "jsonParsed", "commitment": "confirmed"}
        ]
        
        # 获取所有代币账户
        result = make_rpc_request("getTokenAccountsByOwner", params)
        
        if result["success"]:
            try:
                accounts = result["result"]["value"]
                logger.info(f"获取到 {len(accounts)} 个代币账户")
                
                # 如果指定了mint，过滤结果
                if mint:
                    filtered_accounts = []
                    for account in accounts:
                        try:
                            account_mint = account["account"]["data"]["parsed"]["info"]["mint"]
                            if account_mint == mint:
                                filtered_accounts.append(account)
                        except (KeyError, TypeError, IndexError) as e:
                            logger.warning(f"处理代币账户时出现索引错误: {str(e)}")
                            continue
                    
                    logger.info(f"过滤后找到 {len(filtered_accounts)} 个{mint}代币账户")
                    
                    if not filtered_accounts:
                        # 如果没有找到对应的代币账户，返回空数组但标记成功
                        return jsonify({
                            "success": True,
                            "accounts": [],
                            "exists": False
                        })
                    
                    accounts = filtered_accounts
                
                # 格式化返回结果
                formatted_accounts = []
                for account in accounts:
                    try:
                        info = account["account"]["data"]["parsed"]["info"]
                        formatted_accounts.append({
                            "address": account["pubkey"],
                            "mint": info["mint"],
                            "owner": info["owner"],
                            "tokenAmount": info["tokenAmount"],
                            "decimals": info["tokenAmount"]["decimals"],
                            "uiAmount": info["tokenAmount"]["uiAmount"]
                        })
                    except (KeyError, TypeError, IndexError) as e:
                        # 跳过无法解析的账户，记录详细错误
                        logger.warning(f"格式化代币账户时出现错误: {str(e)}, 账户: {account.get('pubkey', 'unknown')}")
                        continue
                
                return jsonify({
                    "success": True,
                    "accounts": formatted_accounts,
                    "exists": len(formatted_accounts) > 0
                })
            except (KeyError, TypeError, IndexError) as e:
                # 处理RPC返回值格式异常的情况
                logger.error(f"解析RPC返回值时出现错误: {str(e)}, 返回值: {result}")
                # 返回成功但账户为空的响应，避免前端出错
                return jsonify({
                    "success": True,
                    "accounts": [],
                    "exists": False,
                    "message": "无法解析RPC返回的账户信息"
                })
        else:
            error_msg = result.get("error", "未知错误")
            logger.error(f"RPC请求失败: {error_msg}")
            
            # 对于特定错误（如账户不存在），返回成功但账户为空的响应
            if "not found" in str(error_msg).lower() or "invalid" in str(error_msg).lower():
                return jsonify({
                    "success": True,
                    "accounts": [],
                    "exists": False,
                    "message": str(error_msg)
                })
            
            return jsonify({"success": False, "error": error_msg}), 400
    except Exception as e:
        logger.exception(f"获取代币账户时发生异常: {str(e)}")
        # 返回成功但账户为空的响应，避免前端出错
        return jsonify({
            "success": True,
            "accounts": [],
            "exists": False,
            "message": f"处理请求时出错: {str(e)}"
        })

@solana_api.route('/get_latest_blockhash', methods=['GET'])
def get_latest_blockhash():
    """获取最新的区块哈希，用于构建交易"""
    try:
        result = make_rpc_request(
            "getLatestBlockhash",
            [{"commitment": "confirmed"}]
        )
        
        if result["success"]:
            return jsonify({
                "success": True,
                "blockhash": result["result"]["blockhash"],
                "lastValidBlockHeight": result["result"]["lastValidBlockHeight"]
            })
        else:
            error_msg = result.get("error", "未知错误")
            logger.error(f"获取区块哈希失败: {error_msg}")
            return jsonify({
                "success": False, 
                "error": error_msg,
                "message": "RPC节点未能返回有效的区块哈希"
            }), 400
    except Exception as e:
        logger.exception(f"获取区块哈希时发生异常: {str(e)}")
        
        # 记录错误
        log_error({
            'error_id': str(uuid.uuid4()),
            'level': "ERROR",
            'message': str(e),
            'component': "get_latest_blockhash",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stack_trace': traceback.format_exc(),
            'details': {
                "remote_addr": request.remote_addr
            }
        })
        
        return jsonify({
            "success": False, 
            "error": str(e),
            "message": "获取区块哈希时发生服务器内部错误"
        }), 500

@solana_api.route('/get_token_balance', methods=['GET'])
def get_token_balance():
    """
    获取账户的代币余额
    
    参数:
    - address: 代币账户地址
    """
    try:
        address = request.args.get('address')
        if not address:
            return jsonify({"success": False, "error": "缺少address参数"}), 400
        
        # 获取代币余额
        result = make_rpc_request(
            "getTokenAccountBalance",
            [address, {"commitment": "confirmed"}]
        )
        
        if result["success"]:
            return jsonify({
                "success": True,
                "balance": result["result"]["value"]
            })
        else:
            return jsonify({"success": False, "error": result["error"]}), 400
    except Exception as e:
        logger.exception(f"获取代币余额时发生异常: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@solana_api.route('/check_ata_exists', methods=['GET'])
def check_ata_exists():
    """
    检查关联代币账户是否存在
    
    参数:
    - owner: 钱包公钥
    - mint: 代币Mint地址
    """
    try:
        owner = request.args.get('owner')
        mint = request.args.get('mint')
        
        if not owner or not mint:
            return jsonify({"success": False, "error": "缺少必要参数"}), 400
        
        logger.info(f"检查ATA存在性 - 所有者: {owner}, 代币: {mint}")
        
        # 获取特定代币的账户
        try:
            # 获取所有代币账户并过滤
            response = get_token_accounts()
            
            # 如果get_token_accounts返回的是Response对象，直接返回
            if isinstance(response, Response):
                return response
            
            # 否则可能是内部调用，手动获取数据
            data = request.args.copy()
            data["owner"] = owner
            data["mint"] = mint
            with current_app.test_request_context(f'/api/solana/get_token_accounts?owner={owner}&mint={mint}'):
                response = get_token_accounts()
                
            return response
        
        except Exception as e:
            logger.exception(f"检查ATA存在性时调用get_token_accounts发生异常: {str(e)}")
            # 不抛出错误，而是返回账户不存在
            return jsonify({
                "success": True,
                "accounts": [],
                "exists": False,
                "message": "获取账户信息失败，账户可能不存在"
            })
    
    except Exception as e:
        logger.exception(f"检查ATA存在性时发生异常: {str(e)}")
        # 不抛出错误，而是返回账户不存在
        return jsonify({
            "success": True,
            "accounts": [],
            "exists": False,
            "message": f"处理请求时出错: {str(e)}"
        })

@solana_api.route('/transactions', methods=['GET'])
def get_transactions():
    """获取交易记录"""
    try:
        days = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # 从日志中读取交易记录
        transactions = log_reader.get_transaction_logs(
            days_ago=days, 
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'status': 'success',
            'data': transactions,
            'count': len(transactions),
            'total': log_reader.count_transaction_logs(days_ago=days)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@solana_api.route('/api-logs', methods=['GET'])
def get_api_logs():
    """获取API调用日志"""
    try:
        days = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # 从日志中读取API调用记录
        api_logs = log_reader.get_api_logs(
            days_ago=days, 
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'status': 'success',
            'data': api_logs,
            'count': len(api_logs),
            'total': log_reader.count_api_logs(days_ago=days)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@solana_api.route('/error-logs', methods=['GET'])
def get_error_logs():
    """获取错误日志"""
    try:
        days = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # 从日志中读取错误记录
        error_logs = log_reader.get_error_logs(
            days_ago=days, 
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'status': 'success',
            'data': error_logs,
            'count': len(error_logs),
            'total': log_reader.count_error_logs(days_ago=days)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@solana_api.route('/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    try:
        # 实际情况下应该从日志中读取真实数据
        # 这里返回一些模拟数据
        return jsonify({
            "success": True,
            "api_calls": {
                "total": 245,
                "success_rate": 0.94,
                "daily": [23, 31, 42, 25, 35, 47, 42]
            },
            "transactions": {
                "total": 87,
                "success_rate": 0.92,
                "volume": 12450.75,
                "daily": [8, 12, 15, 9, 13, 18, 12]
            },
            "errors": {
                "total": 18,
                "daily": [2, 3, 1, 4, 2, 3, 3]
            }
        })
    except Exception as e:
        logger.exception(f"获取统计数据时发生异常: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@solana_api.route('/demo-data', methods=['POST'])
def generate_demo_data():
    """生成演示数据（仅用于测试）"""
    try:
        # 创建日志目录
        os.makedirs('logs/solana', exist_ok=True)
        
        # 生成示例交易日志
        transactions = []
        for i in range(50):
            tx_date = datetime.now() - timedelta(hours=i*2)
            tx = {
                'timestamp': tx_date.strftime('%Y-%m-%d %H:%M:%S'),
                'transaction_id': f'demo-tx-{i+1}',
                'wallet_address': f'demo-wallet-{(i % 10) + 1}',
                'type': 'transfer' if i % 3 == 0 else ('mint' if i % 3 == 1 else 'burn'),
                'amount': round(i * 0.05 + 0.1, 2),
                'token': 'SOL',
                'status': 'success' if i % 8 != 0 else 'failed',
                'block_number': 12345678 + i
            }
            transactions.append(tx)
            
        # 写入示例交易日志
        with open('logs/solana/transactions.log', 'w') as f:
            for tx in transactions:
                f.write(json.dumps(tx) + '\n')
                
        # 生成示例API调用日志
        api_logs = []
        for i in range(100):
            log_date = datetime.now() - timedelta(hours=i)
            log = {
                'timestamp': log_date.strftime('%Y-%m-%d %H:%M:%S'),
                'request_id': f'req-{i+1}',
                'method': 'GET' if i % 2 == 0 else 'POST',
                'endpoint': f'/api/solana/{"get_balance" if i % 3 == 0 else ("transfer" if i % 3 == 1 else "mint")}',
                'params': json.dumps({'wallet': f'demo-wallet-{(i % 10) + 1}'}),
                'response_time': round(i * 0.01 + 0.05, 3),
                'status_code': 200 if i % 10 != 0 else (400 if i % 20 == 0 else 500),
                'client_ip': f'192.168.1.{i % 255}'
            }
            api_logs.append(log)
            
        # 写入示例API调用日志
        with open('logs/solana/api_calls.log', 'w') as f:
            for log in api_logs:
                f.write(json.dumps(log) + '\n')
                
        # 生成示例错误日志
        error_logs = []
        for i in range(20):
            log_date = datetime.now() - timedelta(hours=i*5)
            log = {
                'timestamp': log_date.strftime('%Y-%m-%d %H:%M:%S'),
                'error_id': f'err-{i+1}',
                'level': 'ERROR' if i % 3 != 0 else 'CRITICAL',
                'message': f'演示错误信息 {i+1}',
                'component': 'solana_service' if i % 2 == 0 else 'transaction_processor',
                'stack_trace': f'File "app/services/solana_service.py", line {i+10}, in process_transaction\n    raise Exception("演示错误")'
            }
            error_logs.append(log)
            
        # 写入示例错误日志
        with open('logs/solana/errors.log', 'w') as f:
            for log in error_logs:
                f.write(json.dumps(log) + '\n')
                
        return jsonify({
            'status': 'success',
            'message': '示例数据已生成',
            'transactions': len(transactions),
            'api_logs': len(api_logs),
            'error_logs': len(error_logs)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@solana_api.route('/check_account', methods=['GET'])
def check_account_info():
    """
    检查账户信息
    
    参数:
    - address: 账户地址
    """
    try:
        address = request.args.get('address')
        if not address:
            return jsonify({"success": False, "error": "缺少address参数"}), 400
        
        # 获取账户信息
        result = make_rpc_request(
            "getAccountInfo",
            [address, {"encoding": "jsonParsed", "commitment": "confirmed"}]
        )
        
        if result["success"]:
            return jsonify({
                "success": True,
                "exists": result["result"] is not None,
                "account_info": result["result"]
            })
        else:
            return jsonify({"success": False, "error": result["error"]}), 400
    except Exception as e:
        logger.exception(f"检查账户信息时发生异常: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@solana_api.route('/get_balance', methods=['GET'])
def get_balance():
    """
    获取账户SOL余额
    
    参数:
    - address: 账户地址
    """
    try:
        address = request.args.get('address')
        if not address:
            return jsonify({"success": False, "error": "缺少address参数"}), 400
        
        # 获取账户余额
        result = make_rpc_request(
            "getBalance",
            [address, {"commitment": "confirmed"}]
        )
        
        if result["success"]:
            return jsonify({
                "success": True,
                "balance": result["result"],
                "lamports": result["result"]
            })
        else:
            return jsonify({"success": False, "error": result["error"]}), 400
    except Exception as e:
        logger.exception(f"获取账户余额时发生异常: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500 