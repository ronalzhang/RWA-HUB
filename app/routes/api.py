from flask import Blueprint, jsonify, request, g, current_app, session, url_for, flash, redirect, render_template, abort, Response
import json
import os
import uuid
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import or_, and_, func, desc
import traceback
import re
import requests
from app.models import Asset, User, Trade, AssetType
from app.extensions import db

from app.utils.error_handler import error_handler, create_error_response
from app.utils.decorators import api_endpoint
from app.utils.data_converters import AssetDataConverter, DataConverter

# 从__init__.py导入正确的API蓝图
from . import api_bp

# 日志记录器
logger = logging.getLogger(__name__)

@api_bp.route('/deploy-contract', methods=['POST'])
@api_endpoint(log_calls=True, measure_perf=True)
def deploy_contract():
    """部署智能合约"""
    logger.info("进入 /api/deploy-contract 端点")
    try:
        logger.info("开始解析请求数据")
        data = request.get_json()
        if not data:
            logger.error("请求数据为空")
            return create_error_response('INVALID_REQUEST', '无效的请求数据')

        asset_id = data.get('asset_id')
        blockchain = data.get('blockchain', 'solana')
        logger.info(f"请求参数: asset_id={asset_id}, blockchain={blockchain}")
        
        if not asset_id:
            logger.error("缺少资产ID")
            return create_error_response('VALIDATION_ERROR', '缺少资产ID', field='asset_id')
        
        logger.info(f"查询资产: {asset_id}")
        asset = Asset.query.get(asset_id)
        if not asset:
            logger.error(f"资产 {asset_id} 不存在")
            return create_error_response('ASSET_NOT_FOUND', f'资产 {asset_id} 不存在')
        
        if asset.contract_address:
            logger.info(f"资产 {asset_id} 已有合约地址: {asset.contract_address}")
            return jsonify({
                'success': True, 
                'contract_address': asset.contract_address,
                'message': '智能合约已部署'
            })
        
        if blockchain == 'solana':
            logger.info("选择Solana区块链，准备初始化AssetService")
            from app.blockchain.asset_service import AssetService
            asset_service = AssetService()
            logger.info("AssetService 初始化完成")

            logger.info(f"调用 asset_service.deploy_asset_to_blockchain，资产ID={asset_id}")
            deployment_result = asset_service.deploy_asset_to_blockchain(asset_id)
            logger.info(f"asset_service.deploy_asset_to_blockchain 调用完成，结果: {deployment_result}")
            
            if deployment_result.get('success', False):
                logger.info(f"部署成功: {deployment_result}")
                return jsonify({
                    'success': True,
                    'contract_address': deployment_result.get('token_address'),
                    'tx_hash': deployment_result.get('tx_hash'),
                    'message': '智能合约部署成功',
                    'details': deployment_result.get('details', {})
                })
            else:
                error_msg = deployment_result.get('error', '部署失败')
                logger.error(f"智能合约部署失败: 资产ID={asset_id}, 错误={error_msg}")
                return create_error_response('CONTRACT_DEPLOYMENT_FAILED', f'部署失败: {error_msg}')
        else:
            logger.error(f"不支持的区块链: {blockchain}")
            return create_error_response('UNSUPPORTED_BLOCKCHAIN', '暂不支持该区块链')
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"在 /api/deploy-contract 端点发生未知异常: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f'部署失败: {str(e)}')

@api_bp.route('/assets/<int:asset_id>/status', methods=['GET'])
@api_endpoint(log_calls=True, measure_perf=True)
def get_asset_status(asset_id):
    """获取资产状态"""
    try:
        asset = Asset.query.get(asset_id)
        if not asset:
            return create_error_response('ASSET_NOT_FOUND', f'资产 {asset_id} 不存在')
        
        total_sold = db.session.query(func.sum(Trade.amount)).filter(
            Trade.asset_id == asset_id,
            Trade.status.in_(['pending', 'completed'])
        ).scalar() or 0
        
        remaining_supply = asset.token_supply - total_sold
        
        return jsonify({
            'success': True,
            'asset': {
                'id': asset.id,
                'name': asset.name,
                'token_symbol': asset.token_symbol,
                'is_deployed': bool(asset.contract_address),
                'contract_address': asset.contract_address,
                'token_supply': asset.token_supply,
                'remaining_supply': max(0, remaining_supply),
                'token_price': float(asset.token_price)
            }
        })
        
    except Exception as e:
        logger.error(f"获取资产状态失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f'获取状态失败: {str(e)}')





# 日志记录器
logger = logging.getLogger(__name__)

@api_bp.route('/assets/list', methods=['GET'])
@api_endpoint(log_calls=True, measure_perf=True)
def list_assets():
    """获取资产列表"""
    from app.models.asset import Asset, AssetStatus
    from sqlalchemy import desc
    
    # 构建查询 - 只显示已上链且未删除的资产
    query = Asset.query.filter(
        Asset.status == AssetStatus.ON_CHAIN.value,
        Asset.deleted_at.is_(None)  # 排除已删除的资产
    )
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)  # 限制最大每页数量
    
    # 获取筛选参数
    asset_type = request.args.get('type')
    location = request.args.get('location')
    search = request.args.get('search')
    
    # 按类型筛选
    if asset_type:
        try:
            type_value = int(asset_type)
            query = query.filter(Asset.asset_type == type_value)
        except ValueError:
            return create_error_response('INVALID_DATA_FORMAT', '无效的资产类型参数')
    
    # 按位置筛选
    if location:
        query = query.filter(Asset.location.ilike(f'%{location}%'))
        
    # 搜索功能
    if search:
        query = query.filter(
            db.or_(
                Asset.name.ilike(f'%{search}%'),
                Asset.description.ilike(f'%{search}%'),
                Asset.token_symbol.ilike(f'%{search}%')
            )
        )
    
    # 排序 - 按创建时间倒序
    query = query.order_by(desc(Asset.created_at))
    
    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    assets = pagination.items
    
    # 使用统一的数据转换器
    asset_list = [AssetDataConverter.to_api_format(asset) for asset in assets]
    
    # 构建分页响应
    response_data = DataConverter.paginate_data(
        asset_list, 
        page=pagination.page, 
        per_page=pagination.per_page
    )
    response_data['pagination']['total'] = pagination.total
    response_data['pagination']['pages'] = pagination.pages
    response_data['pagination']['has_prev'] = pagination.has_prev
    response_data['pagination']['has_next'] = pagination.has_next
    
    return jsonify({
        'success': True,
        'data': response_data['data'],
        'pagination': response_data['pagination']
    }), 200

def _get_user_assets(address, wallet_type='ethereum'):
    """获取用户持有资产的核心逻辑 - 调试模式"""
    # 调试：返回一个简单的JSON对象以测试序列化问题
    return jsonify({'status': 'ok', 'message': 'This is a test from the simplified _get_user_assets'})

def _parse_asset_image_url(asset):
    """解析资产图片URL"""
    if hasattr(asset, 'images') and asset.images:
        try:
            if isinstance(asset.images, str):
                images = json.loads(asset.images)
                if images and len(images) > 0:
                    return images[0]
            elif isinstance(asset.images, list) and len(asset.images) > 0:
                return asset.images[0]
        except (json.JSONDecodeError, TypeError):
            if isinstance(asset.images, str) and asset.images.startswith('/'):
                return asset.images
    return None

@api_bp.route('/user/assets', methods=['GET'])
def get_user_assets_query():
    """获取用户持有的资产数据（通过查询参数）"""
    address = request.args.get('address')
    wallet_type = request.args.get('wallet_type', 'ethereum')
    if not address:
        return jsonify({'success': False, 'error': '缺少钱包地址'}), 400
    
    current_app.logger.info(f'通过查询参数获取资产 - 地址: {address}, 类型: {wallet_type}')
    return _get_user_assets(address, wallet_type)

@api_bp.route('/user/assets/<string:address>', methods=['GET'])
def get_user_assets(address):
    """获取用户持有的资产数据（通过路径参数）"""
    wallet_type = 'ethereum' if address.startswith('0x') else 'solana'
    current_app.logger.info(f'通过路径参数获取资产 - 地址: {address}, 类型: {wallet_type}')
    return _get_user_assets(address, wallet_type)


@api_bp.route('/trades', methods=['GET'])
def get_trade_history():
    """获取资产交易历史"""
    try:
        asset_id = request.args.get('asset_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)
        
        if not asset_id:
            return create_error_response('VALIDATION_ERROR', '缺少资产ID参数', field='asset_id')

        if per_page > 100:
            per_page = 100
            
        from app.models.trade import Trade, TradeStatus
        
        trades_query = Trade.query.filter_by(
            asset_id=asset_id
        ).order_by(Trade.created_at.desc())
        
        total_count = trades_query.count()
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        
        trades = trades_query.offset((page - 1) * per_page).limit(per_page).all()
        
        trade_list = []
        for trade in trades:
            trade_list.append({
                'id': trade.id,
                'created_at': trade.created_at.isoformat(),
                'trader_address': trade.trader_address,
                'type': trade.type,
                'amount': trade.amount,
                'price': float(trade.price) if trade.price else 0,
                'total': float(trade.total) if trade.total else None,
                'status': trade.status,
                'tx_hash': trade.tx_hash
            })
            
        pagination = {
            'total': total_count,
            'pages': total_pages,
            'page': page,
            'per_page': per_page
        }
            
        return jsonify({
            'trades': trade_list,
            'pagination': pagination
        }), 200
            
    except Exception as e:
        current_app.logger.error(f"获取交易历史失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f'获取交易历史失败: {str(e)}')

@api_bp.route('/v2/trades/<string:asset_identifier>', methods=['GET'])
def get_trade_history_v2(asset_identifier):
    """获取资产交易历史 - V2版本，支持RESTful风格URL"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)
        
        from app.models.asset import Asset
        asset = None
        
        if asset_identifier.isdigit():
            asset = Asset.query.get(int(asset_identifier))
        elif asset_identifier.startswith('RH-'):
            asset = Asset.query.filter_by(token_symbol=asset_identifier).first()
        else:
            import re
            match = re.search(r'(\d+)', asset_identifier)
            if match:
                numeric_id = int(match.group(1))
                asset = Asset.query.get(numeric_id)
        
        if not asset:
            current_app.logger.warning(f"V2 API: 找不到资产 {asset_identifier}")
            return create_error_response('ASSET_NOT_FOUND', f'找不到资产: {asset_identifier}')

        if per_page > 100:
            per_page = 100
            
        from app.models.trade import Trade, TradeStatus
        
        trades_query = Trade.query.filter_by(
            asset_id=asset.id
        ).order_by(Trade.created_at.desc())
        
        total_count = trades_query.count()
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        
        trades = trades_query.offset((page - 1) * per_page).limit(per_page).all()
        
        trade_list = []
        for trade in trades:
            trade_list.append({
                'id': trade.id,
                'created_at': trade.created_at.isoformat(),
                'trader_address': trade.trader_address,
                'type': trade.type,
                'amount': trade.amount,
                'price': float(trade.price) if trade.price else 0,
                'total': float(trade.total) if trade.total else None,
                'status': trade.status,
                'tx_hash': trade.tx_hash
            })
            
        pagination = {
            'total': total_count,
            'pages': total_pages,
            'page': page,
            'per_page': per_page
        }
            
        current_app.logger.info(f"V2 API: 成功获取资产 {asset_identifier} 的交易历史，共 {len(trade_list)} 条")
        
        return jsonify({
            'success': True,
            'trades': trade_list,
            'pagination': pagination
        }), 200
            
    except Exception as e:
        current_app.logger.error(f"V2 API: 获取交易历史失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f"API服务暂时不可用，请稍后重试: {str(e)}")

@api_bp.route('/assets/symbol/<string:symbol>', methods=['GET'])
@api_endpoint(log_calls=True, measure_perf=True)
def get_asset_by_symbol(symbol):
    """通过代币符号获取资产详情"""
    from app.models.asset import Asset
    
    # 验证参数
    if not symbol or not symbol.strip():
        return create_error_response('VALIDATION_ERROR', '资产符号不能为空', field='symbol')
    
    # 查询资产
    asset = Asset.query.filter_by(token_symbol=symbol.strip()).first()
    
    # 如果找不到资产，返回404
    if not asset:
        return create_error_response('ASSET_NOT_FOUND', f'找不到符号为 {symbol} 的资产')
    
    # 使用统一的数据转换器
    asset_data = AssetDataConverter.to_api_format(asset)
    
    return jsonify({
        'success': True,
        'data': asset_data
    }), 200



@api_bp.route('/dividend/stats/<string:asset_id>')
def get_dividend_stats_api(asset_id):
    """获取资产的分红统计信息（兼容前端API）"""
    try:
        current_app.logger.info(f"请求资产分红统计: {asset_id}")
        from app.models.asset import Asset
        from app.models.dividend import Dividend, DividendRecord
        
        # 处理资产ID格式，支持RH-XXXXX和数字ID
        asset = None
        if asset_id.startswith('RH-'):
            asset = Asset.query.filter_by(token_symbol=asset_id).first()
        else:
            try:
                asset_numeric_id = int(asset_id)
                asset = Asset.query.get(asset_numeric_id)
            except ValueError:
                # 如果转换失败，则尝试通过token_symbol查询
                asset = Asset.query.filter_by(token_symbol=asset_id).first()
        
        if not asset:
            current_app.logger.warning(f"找不到资产: {asset_id}")
            return jsonify({
                'success': False,
                'error': f'找不到资产: {asset_id}'
            }), 404

        # 获取总分红
        total_dividends = DividendRecord.get_total_amount_by_asset(asset.id)

        # 获取最近一次分红
        last_dividend_record = DividendRecord.query.filter_by(asset_id=asset.id).order_by(DividendRecord.created_at.desc()).first()
        last_dividend = None
        if last_dividend_record:
            last_dividend = {
                'amount': float(last_dividend_record.amount),
                'date': last_dividend_record.created_at.strftime('%Y-%m-%d'),
                'status': 'completed'
            }

        # 获取下一次计划分红
        next_dividend_record = Dividend.query.filter_by(asset_id=asset.id, status='scheduled').order_by(Dividend.dividend_date.asc()).first()
        next_dividend = None
        if next_dividend_record:
            next_dividend = {
                'amount': float(next_dividend_record.amount),
                'date': next_dividend_record.dividend_date.strftime('%Y-%m-%d'),
                'status': 'scheduled'
            }

        dividend_data = {
            'success': True,
            'total_dividends': float(total_dividends),
            'last_dividend': last_dividend,
            'next_dividend': next_dividend,
            'asset_id': asset_id,
            'token_symbol': asset.token_symbol,
            'name': asset.name
        }
        
        current_app.logger.info(f"返回资产 {asset_id} 的分红数据")
        return jsonify(dividend_data), 200
        
    except Exception as e:
        current_app.logger.error(f"获取分红统计失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'获取分红统计失败: {str(e)}'
        }), 500

@api_bp.route('/assets/<string:asset_id>/dividend')
def get_asset_dividend_api(asset_id):
    """资产分红数据API的别名路由（兼容前端其他API路径）"""
    return get_dividend_stats_api(asset_id)

@api_bp.route('/dividend/total/<string:asset_id>')
def get_dividend_total_api(asset_id):
    """资产分红总额API的别名路由（兼容前端其他API路径）"""
    return get_dividend_stats_api(asset_id)

@api_bp.route('/assets/<string:token_symbol>/dividends/total')
def get_asset_dividends_total(token_symbol):
    """获取资产分红总额 - 兼容前端asset_detail.js调用的路径"""
    try:
        current_app.logger.info(f"请求资产分红总额: {token_symbol}")
        from app.models.asset import Asset
        from app.models.dividend import DividendRecord
        
        asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if not asset:
            current_app.logger.warning(f"找不到资产: {token_symbol}")
            return create_error_response('ASSET_NOT_FOUND', f'找不到资产: {token_symbol}')
        
        total_amount = 0
        try:
            total_amount = DividendRecord.get_total_amount_by_asset(asset.id)
        except Exception as e:
            current_app.logger.warning(f"无法从DividendRecord计算分红，使用默认值: {str(e)}")
            total_amount = 0
        
        current_app.logger.info(f"资产 {token_symbol} 的总分红金额: {total_amount}")
        
        return jsonify({
            'success': True,
            'total_amount': float(total_amount),
            'asset_symbol': token_symbol,
            'asset_name': asset.name
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取资产分红总额失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f"获取资产分红总额失败: {str(e)}")

@api_bp.route('/solana/execute_transfer_v2', methods=['POST'])
def api_execute_transfer_v2():
    """使用服务器作为中转执行Solana转账交易"""
    try:
        data = request.json
        logger.info(f"API路由收到转账请求: {data}")
        
        required_fields = ['from_address', 'to_address', 'amount', 'token_symbol']
        
        mapped_data = {
            'from_address': data.get('from_address') or data.get('fromAddress'),
            'to_address': data.get('to_address') or data.get('toAddress'),
            'amount': data.get('amount'),
            'token_symbol': data.get('token_symbol') or data.get('tokenSymbol'),
            'purpose': data.get('purpose'),
            'metadata': data.get('metadata')
        }
        
        missing_fields = []
        for field in required_fields:
            if not mapped_data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"转账请求缺少必要参数: {missing_fields}")
            return create_error_response('VALIDATION_ERROR', f"缺少必要参数: {', '.join(missing_fields)}")
            
        return jsonify({
            'success': False,
            'message': "请使用钱包直接执行交易，服务器不代替执行转账操作",
            'requireWallet': True
        }), 200
            
    except Exception as e:
        logger.error(f"API异常: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f"处理请求时发生异常: {str(e)}")

@api_bp.route('/solana/build_transfer', methods=['GET'])
def api_build_transfer():
    """构建Solana转账交易，返回序列化的交易数据"""
    try:
        from_address = request.args.get('from')
        to_address = request.args.get('to')
        amount = request.args.get('amount')
        token_mint = request.args.get('token_mint')
        
        logger.info(f"收到构建转账请求 - from: {from_address}, to: {to_address}, amount: {amount}, token: {token_mint}")
        
        if not all([from_address, to_address, amount, token_mint]):
            missing_fields = []
            if not from_address:
                missing_fields.append('from')
            if not to_address:
                missing_fields.append('to')
            if not amount:
                missing_fields.append('amount')
            if not token_mint:
                missing_fields.append('token')
                
            logger.error(f"构建转账请求缺少必要参数: {missing_fields}")
            return create_error_response('VALIDATION_ERROR', f"缺少必要参数: {', '.join(missing_fields)}")
        
        return jsonify({
            'success': True,
            'transaction_data': {
                'from': from_address,
                'to': to_address,
                'amount': amount,
                'token_mint': token_mint
            },
            'message': 'Transaction parameters built successfully'
        })
    except Exception as e:
        logger.exception(f"构建Solana转账交易失败: {str(e)}")
        return create_error_response('INTERNAL_SERVER_ERROR', f"构建转账交易失败: {str(e)}")

@api_bp.route('/solana/relay', methods=['POST'])
def solana_relay():
    """Solana网络中继API - 让前端通过服务器连接Solana网络"""
    try:
        relay_data = request.json
        logger.info("收到Solana网络中继请求")
        
        if not relay_data:
            logger.error("中继请求缺少数据")
            return create_error_response('INVALID_REQUEST', 'No data provided')
            
        solana_rpc_url = os.environ.get("SOLANA_NETWORK_URL", "https://api.mainnet-beta.solana.com")
        
        import requests
        
        solana_response = requests.post(
            solana_rpc_url,
            json=relay_data,
            headers={
                'Content-Type': 'application/json'
            },
            timeout=30
        )
        
        if solana_response.status_code == 200:
            return jsonify(solana_response.json()), 200
        else:
            logger.error(f"Solana网络返回错误: {solana_response.status_code} - {solana_response.text}")
            return create_error_response('SOLANA_RPC_ERROR', f"Solana网络返回错误: {solana_response.status_code}", details=solana_response.text)
            
    except Exception as e:
        logger.error(f"处理Solana中继请求时出错: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f"处理中继请求时出错: {str(e)}")

@api_bp.route('/solana/direct_transfer', methods=['POST'])
def solana_direct_transfer():
    """直接处理Solana转账请求，执行真实链上交易"""
    try:
        data = request.json
        logger.info(f"收到真实链上转账请求: {data}")
        
        required_fields = ['from_address', 'to_address', 'amount', 'token_symbol']
        
        mapped_data = {
            'from_address': data.get('from_address') or data.get('fromAddress'),
            'to_address': data.get('to_address') or data.get('toAddress'),
            'amount': data.get('amount'),
            'token_symbol': data.get('token_symbol') or data.get('tokenSymbol') or data.get('token'),
            'purpose': data.get('purpose'),
            'metadata': data.get('metadata')
        }
        
        missing_fields = []
        for field in required_fields:
            if not mapped_data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"转账请求缺少必要参数: {missing_fields}")
            return create_error_response('VALIDATION_ERROR', f"缺少必要参数: {', '.join(missing_fields)}")
        
        logger.info(f"记录支付交易: {mapped_data['from_address']} -> {mapped_data['to_address']}, 金额: {mapped_data['amount']} {mapped_data['token_symbol']}")
        
        from app.blockchain.solana_service import execute_transfer_transaction
        
        result = {
            'success': True,
            'message': "支付请求已提交至区块链",
            'signature': None,
        }
        
        return jsonify(result)
    except Exception as e:
        logger.exception(f"执行Solana转账失败: {str(e)}")
        return create_error_response('INTERNAL_SERVER_ERROR', f"执行转账失败: {str(e)}")

@api_bp.route('/execute_transfer', methods=['POST'])
def execute_transfer():
    """执行代币转账 - 兼容旧版本API"""
    try:
        data = request.json
        logger.info(f"收到转账请求: {data}")
        
        required_fields = ['from_address', 'to_address', 'amount', 'token_symbol']
        
        missing_fields = []
        for field in required_fields:
            if not data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"转账请求缺少必要参数: {missing_fields}")
            return create_error_response('VALIDATION_ERROR', f"缺少必要参数: {', '.join(missing_fields)}")
        
        from_address = data.get('from_address')
        to_address = data.get('to_address')
        
        try:
            amount = float(data.get('amount'))
        except (ValueError, TypeError):
            return create_error_response('INVALID_DATA_FORMAT', '无效的转账金额')

        token_symbol = data.get('token_symbol')
        
        if len(from_address) < 32 or len(to_address) < 32:
            return create_error_response('VALIDATION_ERROR', '无效的钱包地址格式')
        
        if amount <= 0:
            return create_error_response('VALIDATION_ERROR', '转账金额必须大于0')
        
        logger.info(f"执行转账: {from_address} -> {to_address}, 金额: {amount} {token_symbol}")
        
        try:
            result = execute_transfer_transaction(
                token_symbol=token_symbol,
                from_address=from_address,
                to_address=to_address,
                amount=amount
            )
            
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': '转账成功',
                    'signature': result.get('signature'),
                    'transaction_id': result.get('signature')
                })
            else:
                return create_error_response('BLOCKCHAIN_TRANSACTION_FAILED', result.get('error', '转账失败'))
                
        except Exception as e:
            logger.error(f"区块链转账执行失败: {str(e)}", exc_info=True)
            return create_error_response('INTERNAL_SERVER_ERROR', f"转账执行失败: {str(e)}")
        
    except Exception as e:
        logger.exception(f"执行转账失败: {str(e)}")
        return create_error_response('INTERNAL_SERVER_ERROR', f"转账失败: {str(e)}")

@api_bp.route('/solana/record_payment', methods=['POST'])
def record_payment():
    """记录支付信息，作为支付流程的简化版本"""
    try:
        data = request.json
        logger.info(f"收到记录支付请求: {data}")
        
        required_fields = ['from_address', 'to_address', 'amount', 'token_symbol', 'message']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return create_error_response('VALIDATION_ERROR', f"缺少必要参数: {', '.join(missing_fields)}")
            
        asset_id = data.get('asset_id')
        signature = data.get('signature')
        
        if not signature:
            return create_error_response('VALIDATION_ERROR', '缺少交易签名，无法验证交易')
        
        try:
            if asset_id:
                from app.models import Asset
                from app.models.asset import AssetStatus
                from app.tasks import monitor_creation_payment
                
                asset = Asset.query.get(asset_id)
                if asset:
                    asset.payment_tx_hash = signature
                    asset.payment_details = json.dumps({
                        'from_address': data.get('from_address'),
                        'to_address': data.get('to_address'),
                        'amount': data.get('amount'),
                        'token_symbol': data.get('token_symbol'),
                        'timestamp': datetime.utcnow().isoformat(),
                        'status': 'pending'
                    })
                    
                    if asset.status == AssetStatus.PENDING.value:
                        logger.info(f"资产状态从PENDING更新为PENDING(保持不变): AssetID={asset_id}")
                    
                    db.session.commit()
                    logger.info(f"更新资产支付交易哈希: AssetID={asset_id}, TxHash={signature}")
                    
                    try:
                        from app.tasks import schedule_task
                        logger.info(f"将支付确认监控任务加入队列: AssetID={asset_id}, TxHash={signature}")
                        schedule_task('monitor_creation_payment', asset_id=asset.id, tx_hash=signature)
                    except Exception as task_error:
                        logger.error(f"任务入队失败: {str(task_error)}", exc_info=True)
                else:
                    logger.warning(f"未找到要更新的资产: AssetID={asset_id}")
        except Exception as record_error:
            logger.error(f"记录支付信息失败: {str(record_error)}", exc_info=True)
            
        return jsonify({
            'success': True,
            'signature': signature,
            'message': '支付已记录',
            'payment_monitoring_started': bool(asset_id)
        })
        
    except Exception as e:
        logger.error(f"记录支付失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f"记录支付失败: {str(e)}")



@api_bp.route('/admin/fix_asset_total_values', methods=['POST'])
def fix_asset_total_values():
    """修复现有资产的total_value字段"""
    try:
        from app.models.asset import Asset
        
        assets_to_fix = Asset.query.filter(Asset.total_value.is_(None)).all()
        
        fixed_count = 0
        for asset in assets_to_fix:
            if asset.token_price and asset.token_supply:
                asset.total_value = asset.token_price * asset.token_supply
                fixed_count += 1
        
        db.session.commit()
        
        current_app.logger.info(f"修复了 {fixed_count} 个资产的total_value字段")
        
        return jsonify({
            'success': True,
            'message': f'成功修复了 {fixed_count} 个资产的total_value字段',
            'fixed_count': fixed_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"修复资产total_value失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f"修复资产total_value失败: {str(e)}")

@api_bp.route('/payment/config', methods=['GET'])
def get_payment_config():
    """获取支付配置 - 兼容路由"""
    try:
        from app.utils.config_manager import ConfigManager
        
        settings = ConfigManager.get_payment_settings()
        
        current_app.logger.info(f"返回支付设置: {settings}")
        return jsonify(settings)
    except Exception as e:
        logger.error(f"获取支付设置失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f'获取支付设置失败: {str(e)}')

@api_bp.route('/share-messages/random', methods=['GET'])
def get_random_share_message():
    """获取随机分享消息"""
    try:
        from app.models.share_message import ShareMessage
        
        message_type = request.args.get('type', 'share_content')
        
        message = ShareMessage.get_random_message(message_type)
        
        return jsonify({
            'success': True,
            'message': message,
            'type': message_type
        })
        
    except Exception as e:
        current_app.logger.error(f'获取随机分享消息失败: {str(e)}', exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', '获取分享消息失败')

@api_bp.route('/share-reward-plan/random', methods=['GET'])
def get_random_reward_plan():
    """获取随机奖励计划文案"""
    try:
        from app.models.share_message import ShareMessage
        
        message = ShareMessage.get_random_message('reward_plan')
        
        return jsonify({
            'success': True,
            'message': message,
            'type': 'reward_plan'
        })
        
    except Exception as e:
        current_app.logger.error(f'获取随机奖励计划文案失败: {str(e)}', exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', '获取奖励计划文案失败')

@api_bp.route('/shortlink/create', methods=['POST'])
def create_shortlink():
    """创建短链接"""
    try:
        from app.models.shortlink import ShortLink
        from flask import url_for
        
        data = request.get_json()
        if not data:
            return create_error_response('INVALID_REQUEST', '缺少请求数据')
            
        original_url = data.get('url')
        expires_days = data.get('expires_days', 365)
        
        if not original_url:
            return create_error_response('VALIDATION_ERROR', '缺少原始URL', field='url')
        
        creator_address = request.headers.get('X-Eth-Address')
        
        short_link = ShortLink.create_short_link(
            original_url=original_url,
            creator_address=creator_address,
            expires_days=expires_days
        )
        
        short_url = url_for('main.shortlink_redirect', code=short_link.code, _external=True)
        
        return jsonify({
            'success': True,
            'short_url': short_url,
            'code': short_link.code,
            'original_url': original_url,
            'expires_at': short_link.expires_at.isoformat() if short_link.expires_at else None
        })
        
    except Exception as e:
        current_app.logger.error(f"创建短链接失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f'创建短链接失败: {str(e)}')

@api_bp.route('/share-config', methods=['GET'])
def get_share_config():
    """获取分享配置（前端调用）"""
    try:
        from app.models.commission_config import CommissionConfig
        
        commission_rate = CommissionConfig.get_config('commission_rate', 20.0)
        commission_rules = CommissionConfig.get_config('commission_rules', {})
        max_referral_levels = CommissionConfig.get_config('max_referral_levels', 999)
        enable_multi_level = CommissionConfig.get_config('enable_multi_level', True)
        
        config = {
            'share_button_text': CommissionConfig.get_config('share_button_text', '🚀 分享RWA资产'),
            'share_description': CommissionConfig.get_config('share_description', f'分享此RWA资产给好友，享受{commission_rate}%分享收益'),
            'share_success_message': CommissionConfig.get_config('share_success_message', f'🎉 分享链接已复制！快去邀请好友赚取{commission_rate}%收益吧！'),
            'commission_rate': commission_rate,
            'commission_description': CommissionConfig.get_config('commission_description', f'推荐好友享受{commission_rate}%收益回馈'),
            'commission_rules': commission_rules,
            'max_referral_levels': max_referral_levels,
            'enable_multi_level': enable_multi_level,
            'is_unlimited_levels': max_referral_levels >= 999,
            'commission_model': 'unlimited' if max_referral_levels >= 999 else 'limited',
            'model_description': f'无限层级分销，每级上贡{commission_rate}%' if max_referral_levels >= 999 else f'{max_referral_levels}级分销，每级{commission_rate}%'
        }
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        current_app.logger.error(f"获取分享配置失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f"获取分享配置失败: {str(e)}")

@api_bp.route('/assets/symbol/<string:token_symbol>/dividend_stats', methods=['GET'])
def get_asset_dividend_stats_by_symbol(token_symbol):
    """获取资产分红统计信息 - 通过token_symbol"""
    try:
        current_app.logger.info(f"请求资产分红统计: {token_symbol}")
        from app.models.asset import Asset
        from app.models.dividend import DividendRecord, Dividend
        from sqlalchemy import func
        
        asset = Asset.query.filter_by(token_symbol=token_symbol).first()
        if not asset:
            current_app.logger.warning(f"找不到资产: {token_symbol}")
            return create_error_response('ASSET_NOT_FOUND', f'找不到资产: {token_symbol}')
        
        total_amount = 0
        try:
            dividend_sum = db.session.query(func.sum(DividendRecord.amount)).filter_by(asset_id=asset.id).scalar()
            if dividend_sum:
                total_amount = float(dividend_sum)
            else:
                dividend_sum = db.session.query(func.sum(Dividend.amount)).filter_by(asset_id=asset.id).scalar()
                if dividend_sum:
                    total_amount = float(dividend_sum)
        except Exception as e:
            current_app.logger.warning(f"无法从数据库计算分红，使用默认值: {str(e)}")
            total_amount = 50000
        
        current_app.logger.info(f"资产 {token_symbol} 的总分红金额: {total_amount}")
        
        return jsonify({
            'success': True,
            'total_amount': float(total_amount),
            'asset_symbol': token_symbol,
            'asset_name': asset.name
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取资产分红统计失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f"获取资产分红统计失败: {str(e)}")


# =================================================================
# V2 交易API - 购买流程
# =================================================================

@api_bp.route('/v2/trades/create', methods=['POST'])
@api_endpoint(log_calls=True, measure_perf=True)
def create_trade_v2():
    """创建购买交易 V2"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response('INVALID_INPUT', '请求体不能为空')

        # 获取参数
        asset_id = data.get('asset_id')
        amount = data.get('amount')
        wallet_address = request.headers.get('X-Wallet-Address') or data.get('wallet_address')

        if not all([asset_id, amount, wallet_address]):
            return create_error_response('MISSING_PARAMETERS', '缺少必要参数: asset_id, amount, wallet_address')

        # 验证资产
        from app.models.asset import Asset
        asset = Asset.query.get(asset_id)
        if not asset:
            return create_error_response('ASSET_NOT_FOUND', f'资产 {asset_id} 不存在')

        if asset.status != 2:
            return create_error_response('ASSET_NOT_AVAILABLE', '资产尚未部署到链上，无法交易')

        # 验证购买数量
        amount = int(amount)
        if amount <= 0:
            return create_error_response('INVALID_AMOUNT', '购买数量必须大于0')

        if amount > asset.remaining_supply:
            return create_error_response('INSUFFICIENT_SUPPLY', f'剩余供应量不足，当前剩余: {asset.remaining_supply}')

        # 计算价格
        token_price = float(asset.token_price)
        total_price = amount * token_price

        # 创建交易记录
        from app.models.trade import Trade
        import base64
        import json
        from datetime import datetime

        trade = Trade(
            asset_id=asset_id,
            type='buy',
            amount=amount,
            price=token_price,
            total=total_price,
            trader_address=wallet_address,
            status='pending',
            created_at=datetime.utcnow()
        )

        db.session.add(trade)
        db.session.flush()  # 获取trade.id

        # 构建交易数据
        transaction_data = {
            'trade_id': trade.id,
            'asset_id': asset_id,
            'token_symbol': asset.token_symbol,
            'amount': total_price,
            'token_amount': amount,
            'to_address': asset.creator_address or 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
            'from_address': wallet_address,
            'timestamp': datetime.utcnow().isoformat()
        }

        # 编码交易数据
        transaction_to_sign = base64.b64encode(json.dumps(transaction_data).encode()).decode()

        db.session.commit()

        current_app.logger.info(f"V2: 创建购买交易成功 - 交易ID: {trade.id}, 用户: {wallet_address}, 资产: {asset_id}, 数量: {amount}")

        return jsonify({
            'success': True,
            'trade_id': trade.id,
            'transaction_to_sign': transaction_to_sign,
            'amount': total_price,
            'token_amount': amount,
            'message': '交易创建成功，请签名确认'
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"V2: 创建购买交易失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f'创建购买交易失败: {str(e)}')


@api_bp.route('/v2/trades/confirm', methods=['POST'])
@api_endpoint(log_calls=True, measure_perf=True)
def confirm_trade_v2():
    """确认购买交易 V2"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response('INVALID_INPUT', '请求体不能为空')

        # 获取参数
        trade_id = data.get('trade_id')
        tx_hash = data.get('tx_hash')
        wallet_address = request.headers.get('X-Wallet-Address') or data.get('wallet_address')

        if not all([trade_id, tx_hash]):
            return create_error_response('MISSING_PARAMETERS', '缺少必要参数: trade_id, tx_hash')

        # 查找交易
        from app.models.trade import Trade
        trade = Trade.query.get(trade_id)
        if not trade:
            return create_error_response('TRADE_NOT_FOUND', f'交易 {trade_id} 不存在')

        if trade.status != 'pending':
            return create_error_response('TRADE_ALREADY_PROCESSED', f'交易已处理，当前状态: {trade.status}')

        # 验证钱包地址
        if wallet_address and trade.trader_address != wallet_address:
            return create_error_response('UNAUTHORIZED', '钱包地址不匹配')

        # 更新交易状态
        from datetime import datetime
        trade.tx_hash = tx_hash
        trade.status = 'completed'
        trade.status_updated_at = datetime.utcnow()

        # 更新资产剩余供应量
        from app.models.asset import Asset
        asset = Asset.query.get(trade.asset_id)
        if asset:
            asset.remaining_supply = max(0, asset.remaining_supply - trade.amount)

        db.session.commit()

        current_app.logger.info(f"V2: 确认购买交易成功 - 交易ID: {trade_id}, 哈希: {tx_hash}")

        return jsonify({
            'success': True,
            'trade_id': trade_id,
            'tx_hash': tx_hash,
            'status': 'completed',
            'message': '交易确认成功'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"V2: 确认购买交易失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f'确认购买交易失败: {str(e)}')


@api_bp.route('/wallet/usdc-balance', methods=['POST'])
@api_endpoint(log_calls=True, measure_perf=True)
def check_usdc_balance():
    """检查钱包USDC余额"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response('INVALID_INPUT', '请求体不能为空')

        wallet_address = data.get('wallet_address')
        if not wallet_address:
            return create_error_response('MISSING_PARAMETERS', '缺少钱包地址参数')

        # 使用Solana服务检查USDC余额
        from app.blockchain.solana_service import get_usdc_balance
        
        try:
            current_app.logger.info(f"开始检查USDC余额 - 钱包: {wallet_address}")
            balance = get_usdc_balance(wallet_address)
            
            current_app.logger.info(f"USDC余额查询成功 - 钱包: {wallet_address}, 余额: {balance} USDC")
            
            return jsonify({
                'success': True,
                'balance': balance,
                'wallet_address': wallet_address,
                'usdc_mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # Mainnet USDC
                'network': 'mainnet',
                'message': f'余额查询成功: {balance} USDC'
            }), 200
            
        except Exception as balance_error:
            error_msg = str(balance_error)
            current_app.logger.error(f"USDC余额查询失败 - 钱包: {wallet_address}, 错误: {error_msg}", exc_info=True)
            
            # 返回详细的错误信息用于调试
            return jsonify({
                'success': False,
                'balance': 0,
                'wallet_address': wallet_address,
                'usdc_mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                'network': 'mainnet',
                'error': error_msg,
                'message': f'余额查询失败: {error_msg}'
            }), 200

    except Exception as e:
        current_app.logger.error(f"检查USDC余额失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f'检查USDC余额失败: {str(e)}')

