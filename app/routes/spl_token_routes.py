from flask import Blueprint, request, jsonify, render_template
from flask_limiter.util import get_remote_address
import logging
import time

from app.models import Asset
from app.services.spl_token_service import SplTokenService
from app.utils.response_helpers import success_response, error_response
from app.extensions import limiter, db

spl_token_bp = Blueprint('spl_token', __name__)
logger = logging.getLogger(__name__)


@spl_token_bp.route('/api/admin/spl-token/create', methods=['POST'])
@limiter.limit("5 per minute")
def create_spl_token():
    """
    为指定资产创建SPL Token

    Body Parameters:
        asset_id (int): 资产ID

    Returns:
        json: 创建结果
    """
    try:
        data = request.get_json()
        if not data:
            return error_response('INVALID_REQUEST', 'Missing request body')

        asset_id = data.get('asset_id')
        if not asset_id:
            return error_response('MISSING_ASSET_ID', 'Asset ID is required')

        # 验证资产存在
        asset = Asset.query.get(asset_id)
        if not asset:
            return error_response('ASSET_NOT_FOUND', f'Asset with ID {asset_id} not found')

        # 检查资产状态
        if asset.status != 2:  # AssetStatus.APPROVED
            return error_response('ASSET_NOT_APPROVED', 'Only approved assets can have SPL tokens created')

        # 检查是否已经创建过SPL Token
        if asset.spl_mint_address:
            return success_response({
                'message': 'SPL Token already exists for this asset',
                'mint_address': asset.spl_mint_address,
                'creation_status': asset.spl_creation_status
            })

        logger.info(f"Admin request to create SPL Token for asset {asset_id} ({asset.token_symbol})")

        # 调用SPL Token服务创建代币
        result = SplTokenService.create_asset_token(asset_id)

        if result.get('success'):
            logger.info(f"SPL Token created successfully for asset {asset_id}: {result.get('data', {}).get('mint_address')}")
            return success_response(result.get('data'))
        else:
            logger.error(f"SPL Token creation failed for asset {asset_id}: {result.get('message')}")
            return error_response(result.get('error'), result.get('message'))

    except Exception as e:
        logger.error(f"Create SPL Token API error: {e}", exc_info=True)
        return error_response('INTERNAL_ERROR', f'Internal server error: {str(e)}')


@spl_token_bp.route('/api/admin/spl-token/mint', methods=['POST'])
@limiter.limit("10 per minute")
def mint_spl_tokens():
    """
    Mint SPL代币给指定用户

    Body Parameters:
        asset_id (int): 资产ID
        user_address (str): 用户钱包地址
        amount (int): mint数量

    Returns:
        json: mint结果
    """
    try:
        data = request.get_json()
        if not data:
            return error_response('INVALID_REQUEST', 'Missing request body')

        asset_id = data.get('asset_id')
        user_address = data.get('user_address')
        amount = data.get('amount')

        if not all([asset_id, user_address, amount]):
            return error_response('MISSING_PARAMETERS', 'asset_id, user_address, and amount are required')

        # 验证数量
        try:
            amount = int(amount)
            if amount <= 0:
                return error_response('INVALID_AMOUNT', 'Amount must be positive integer')
        except (ValueError, TypeError):
            return error_response('INVALID_AMOUNT', 'Amount must be a valid integer')

        # 验证资产
        asset = Asset.query.get(asset_id)
        if not asset:
            return error_response('ASSET_NOT_FOUND', f'Asset with ID {asset_id} not found')

        if not asset.spl_mint_address:
            return error_response('NO_SPL_TOKEN', 'Asset does not have an SPL token. Create one first.')

        logger.info(f"Admin request to mint {amount} tokens of asset {asset_id} to user {user_address}")

        # 调用mint服务
        result = SplTokenService.mint_tokens_to_user(
            mint_address=asset.spl_mint_address,
            user_address=user_address,
            amount=amount,
            asset_id=asset_id
        )

        if result.get('success'):
            logger.info(f"Successfully minted {amount} tokens to user {user_address}")
            return success_response(result.get('data'))
        else:
            logger.error(f"Mint failed: {result.get('message')}")
            return error_response(result.get('error'), result.get('message'))

    except Exception as e:
        logger.error(f"Mint SPL Token API error: {e}", exc_info=True)
        return error_response('INTERNAL_ERROR', f'Internal server error: {str(e)}')


@spl_token_bp.route('/api/spl-token/supply/<mint_address>', methods=['GET'])
@limiter.limit("30 per minute")
def get_token_supply(mint_address):
    """
    获取SPL代币的供应量信息

    Path Parameters:
        mint_address (str): Token mint地址

    Returns:
        json: 供应量信息
    """
    try:
        result = SplTokenService.get_token_supply(mint_address)

        if result.get('success'):
            return success_response(result.get('data'))
        else:
            return error_response(result.get('error'), result.get('message'))

    except Exception as e:
        logger.error(f"Get token supply API error: {e}", exc_info=True)
        return error_response('INTERNAL_ERROR', f'Internal server error: {str(e)}')


@spl_token_bp.route('/api/spl-token/balance/<user_address>/<mint_address>', methods=['GET'])
@limiter.limit("30 per minute")
def get_user_token_balance(user_address, mint_address):
    """
    获取用户的SPL代币余额

    Path Parameters:
        user_address (str): 用户钱包地址
        mint_address (str): Token mint地址

    Returns:
        json: 用户代币余额
    """
    try:
        result = SplTokenService.get_user_token_balance(user_address, mint_address)

        if result.get('success'):
            return success_response(result.get('data'))
        else:
            return error_response(result.get('error'), result.get('message'))

    except Exception as e:
        logger.error(f"Get user token balance API error: {e}", exc_info=True)
        return error_response('INTERNAL_ERROR', f'Internal server error: {str(e)}')


@spl_token_bp.route('/api/admin/spl-token/status/<int:asset_id>', methods=['GET'])
@limiter.limit("30 per minute")
def get_asset_spl_status(asset_id):
    """
    获取资产的SPL Token创建状态

    Path Parameters:
        asset_id (int): 资产ID

    Returns:
        json: SPL Token状态信息
    """
    try:
        asset = Asset.query.get(asset_id)
        if not asset:
            return error_response('ASSET_NOT_FOUND', f'Asset with ID {asset_id} not found')

        status_map = {
            0: 'pending',
            1: 'creating',
            2: 'completed',
            3: 'failed'
        }

        data = {
            'asset_id': asset_id,
            'asset_symbol': asset.token_symbol,
            'spl_mint_address': asset.spl_mint_address,
            'creation_status': status_map.get(asset.spl_creation_status, 'unknown'),
            'creation_tx_hash': asset.spl_creation_tx_hash,
            'created_at': asset.spl_created_at.isoformat() if asset.spl_created_at else None,
            'has_mint_authority': bool(asset.mint_authority_keypair)
        }

        # 如果有mint地址，获取链上供应量信息
        if asset.spl_mint_address:
            supply_result = SplTokenService.get_token_supply(asset.spl_mint_address)
            if supply_result.get('success'):
                data['on_chain_supply'] = supply_result.get('data', {})

        return success_response(data)

    except Exception as e:
        logger.error(f"Get SPL status API error: {e}", exc_info=True)
        return error_response('INTERNAL_ERROR', f'Internal server error: {str(e)}')


@spl_token_bp.route('/api/spl-token/metadata/<mint_address>', methods=['GET'])
@limiter.limit("30 per minute")
def get_token_metadata(mint_address):
    """
    获取SPL Token元数据

    Path Parameters:
        mint_address (str): Token mint地址

    Returns:
        json: Token元数据信息
    """
    try:
        result = SplTokenService.get_token_metadata(mint_address)
        if result['success']:
            return success_response(data=result['data'], message="获取Token元数据成功")
        else:
            return error_response(message=result['message'], error_code=result['error'])
    except Exception as e:
        logger.error(f"获取Token元数据API异常: {e}", exc_info=True)
        return error_response(message=f"获取Token元数据失败: {str(e)}")


@spl_token_bp.route('/api/admin/spl-token/refresh-metadata', methods=['POST'])
@limiter.limit("5 per minute")
def refresh_token_metadata():
    """
    刷新Token元数据（管理员功能）

    Body Parameters:
        asset_id (int): 资产ID

    Returns:
        json: 刷新结果
    """
    try:
        data = request.get_json()
        asset_id = data.get('asset_id')

        if not asset_id:
            return error_response(message="资产ID不能为空")

        # 获取资产
        asset = Asset.query.get(asset_id)
        if not asset:
            return error_response(message="资产不存在")

        if not asset.spl_mint_address:
            return error_response(message="该资产尚未创建SPL Token")

        # 重新生成元数据
        operation_id = f"refresh_metadata_{asset_id}_{int(time.time())}"
        metadata_result = SplTokenService._create_token_metadata(asset, operation_id)

        if metadata_result['success']:
            # 更新数据库中的元数据URI
            asset.metadata_uri = metadata_result['data']['metadata_uri']
            db.session.commit()

            return success_response(
                data=metadata_result['data'],
                message="Token元数据刷新成功"
            )
        else:
            return error_response(
                message=metadata_result['message'],
                error_code=metadata_result['error']
            )

    except Exception as e:
        logger.error(f"刷新Token元数据API异常: {e}", exc_info=True)
        return error_response(message=f"刷新Token元数据失败: {str(e)}")


@spl_token_bp.route('/api/spl-token/transfer', methods=['POST'])
@limiter.limit("10 per minute")
def transfer_tokens():
    """
    转移SPL Token给其他用户

    Body Parameters:
        mint_address (str): Token mint地址
        from_address (str): 发送者钱包地址
        to_address (str): 接收者钱包地址
        amount (int): 转移数量
        from_private_key (str, optional): 发送者私钥

    Returns:
        json: 转移结果
    """
    try:
        data = request.get_json()
        if not data:
            return error_response(message="请求体不能为空")

        mint_address = data.get('mint_address')
        from_address = data.get('from_address')
        to_address = data.get('to_address')
        amount = data.get('amount')
        from_private_key = data.get('from_private_key')

        # 验证必填参数
        if not all([mint_address, from_address, to_address, amount]):
            return error_response(message="mint_address、from_address、to_address和amount为必填参数")

        # 验证数量
        try:
            amount = int(amount)
            if amount <= 0:
                return error_response(message="转移数量必须大于0")
        except (ValueError, TypeError):
            return error_response(message="amount必须为有效整数")

        logger.info(f"Token转移请求: {amount} 个 {mint_address[:8]}... 从 {from_address[:8]}... 到 {to_address[:8]}...")

        # 调用转移服务
        result = SplTokenService.transfer_tokens(
            mint_address=mint_address,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            from_private_key=from_private_key
        )

        if result.get('success'):
            logger.info(f"Token转移成功: {result.get('data', {}).get('tx_hash')}")
            return success_response(data=result.get('data'), message=result.get('message'))
        else:
            logger.error(f"Token转移失败: {result.get('message')}")
            return error_response(
                message=result.get('message'),
                error_code=result.get('error')
            )

    except Exception as e:
        logger.error(f"Token转移API异常: {e}", exc_info=True)
        return error_response(message=f"Token转移失败: {str(e)}")


@spl_token_bp.route('/api/admin/spl-token/burn', methods=['POST'])
@limiter.limit("5 per minute")
def burn_tokens():
    """
    销毁SPL Token（管理员功能）

    Body Parameters:
        mint_address (str): Token mint地址
        owner_address (str): Token拥有者钱包地址
        amount (int): 销毁数量
        owner_private_key (str, optional): 拥有者私钥

    Returns:
        json: 销毁结果
    """
    try:
        data = request.get_json()
        if not data:
            return error_response(message="请求体不能为空")

        mint_address = data.get('mint_address')
        owner_address = data.get('owner_address')
        amount = data.get('amount')
        owner_private_key = data.get('owner_private_key')

        # 验证必填参数
        if not all([mint_address, owner_address, amount]):
            return error_response(message="mint_address、owner_address和amount为必填参数")

        # 验证数量
        try:
            amount = int(amount)
            if amount <= 0:
                return error_response(message="销毁数量必须大于0")
        except (ValueError, TypeError):
            return error_response(message="amount必须为有效整数")

        logger.info(f"Token销毁请求: {amount} 个 {mint_address[:8]}... 拥有者: {owner_address[:8]}...")

        # 调用销毁服务
        result = SplTokenService.burn_tokens(
            mint_address=mint_address,
            owner_address=owner_address,
            amount=amount,
            owner_private_key=owner_private_key
        )

        if result.get('success'):
            logger.info(f"Token销毁成功: {result.get('data', {}).get('tx_hash')}")
            return success_response(data=result.get('data'), message=result.get('message'))
        else:
            logger.error(f"Token销毁失败: {result.get('message')}")
            return error_response(
                message=result.get('message'),
                error_code=result.get('error')
            )

    except Exception as e:
        logger.error(f"Token销毁API异常: {e}", exc_info=True)
        return error_response(message=f"Token销毁失败: {str(e)}")


@spl_token_bp.route('/api/admin/spl-token/list', methods=['GET'])
@limiter.limit("30 per minute")
def list_spl_tokens():
    """
    获取SPL Token列表（管理员功能）

    Returns:
        json: SPL Token列表
    """
    try:
        # 查询所有有SPL Token字段的资产
        assets = Asset.query.filter(
            Asset.spl_creation_status.isnot(None)
        ).order_by(Asset.created_at.desc()).all()

        tokens = []
        for asset in assets:
            token_data = {
                'asset_id': asset.id,
                'asset_name': asset.name,
                'asset_symbol': asset.token_symbol,
                'spl_mint_address': asset.spl_mint_address,
                'creation_status': SplTokenService._get_status_name(asset.spl_creation_status),
                'creation_tx_hash': asset.spl_creation_tx_hash,
                'created_at': asset.spl_created_at.isoformat() if asset.spl_created_at else None,
                'metadata_uri': asset.metadata_uri,
                'has_mint_authority': bool(asset.mint_authority_keypair)
            }

            # 如果有mint地址，获取链上信息
            if asset.spl_mint_address:
                supply_result = SplTokenService.get_token_supply(asset.spl_mint_address)
                if supply_result.get('success'):
                    token_data['on_chain_supply'] = supply_result.get('data', {})

            tokens.append(token_data)

        return success_response(data=tokens, message="获取SPL Token列表成功")

    except Exception as e:
        logger.error(f"获取SPL Token列表API异常: {e}", exc_info=True)
        return error_response(message=f"获取SPL Token列表失败: {str(e)}")


@spl_token_bp.route('/admin/spl-tokens')
def spl_tokens_page():
    """SPL Token管理页面"""
    return render_template('admin_v2/spl_tokens.html')


# ============================================================================
# 监控和统计相关API
# ============================================================================

@spl_token_bp.route('/api/admin/spl-token/statistics', methods=['GET'])
def get_token_statistics():
    """获取SPL Token统计信息"""
    try:
        logger.info("获取SPL Token统计信息")

        result = SplTokenService.get_token_statistics()

        if result.get('success'):
            return success_response(
                data=result.get('data'),
                message="获取统计信息成功"
            )
        else:
            return error_response(
                error_code=result.get('error', 'STATISTICS_ERROR'),
                message=result.get('message', '获取统计信息失败')
            )

    except Exception as e:
        logger.error(f"获取统计信息API异常: {e}", exc_info=True)
        return error_response(message=f"获取统计信息失败: {str(e)}")


@spl_token_bp.route('/api/spl-token/supply-info/<mint_address>', methods=['GET'])
def get_supply_info(mint_address):
    """获取Token供应量信息"""
    try:
        logger.info(f"获取Token供应量信息: {mint_address}")

        result = SplTokenService.get_token_supply_info(mint_address)

        if result.get('success'):
            return success_response(
                data=result.get('data'),
                message="获取供应量信息成功"
            )
        else:
            return error_response(
                error_code=result.get('error', 'SUPPLY_INFO_ERROR'),
                message=result.get('message', '获取供应量信息失败')
            )

    except Exception as e:
        logger.error(f"获取供应量信息API异常: {e}", exc_info=True)
        return error_response(message=f"获取供应量信息失败: {str(e)}")


@spl_token_bp.route('/api/spl-token/holder-count/<mint_address>', methods=['GET'])
def get_holder_count(mint_address):
    """获取Token持有者数量"""
    try:
        logger.info(f"获取Token持有者数量: {mint_address}")

        result = SplTokenService.get_token_holder_count(mint_address)

        if result.get('success'):
            return success_response(
                data=result.get('data'),
                message="获取持有者数量成功"
            )
        else:
            return error_response(
                error_code=result.get('error', 'HOLDER_COUNT_ERROR'),
                message=result.get('message', '获取持有者数量失败')
            )

    except Exception as e:
        logger.error(f"获取持有者数量API异常: {e}", exc_info=True)
        return error_response(message=f"获取持有者数量失败: {str(e)}")


@spl_token_bp.route('/api/spl-token/activity/<mint_address>', methods=['GET'])
def get_token_activity(mint_address):
    """获取Token活动监控信息"""
    try:
        # 获取时间范围参数（默认24小时）
        hours = request.args.get('hours', 24, type=int)
        if hours <= 0 or hours > 720:  # 最大30天
            hours = 24

        logger.info(f"获取Token活动信息: {mint_address}, 时间范围: {hours}小时")

        result = SplTokenService.monitor_token_activity(mint_address, hours)

        if result.get('success'):
            return success_response(
                data=result.get('data'),
                message="获取活动信息成功"
            )
        else:
            return error_response(
                error_code=result.get('error', 'MONITORING_ERROR'),
                message=result.get('message', '获取活动信息失败')
            )

    except Exception as e:
        logger.error(f"获取活动信息API异常: {e}", exc_info=True)
        return error_response(message=f"获取活动信息失败: {str(e)}")


@spl_token_bp.route('/api/admin/spl-token/dashboard-stats', methods=['GET'])
def get_dashboard_statistics():
    """获取SPL Token仪表板统计信息"""
    try:
        logger.info("获取仪表板统计信息")

        # 获取基础统计
        stats_result = SplTokenService.get_token_statistics()
        if not stats_result.get('success'):
            return error_response(
                error_code=stats_result.get('error', 'STATISTICS_ERROR'),
                message=stats_result.get('message', '获取统计信息失败')
            )

        dashboard_data = stats_result.get('data', {})

        # 添加额外的仪表板信息
        try:
            from app.models import Asset
            from sqlalchemy import func
            from datetime import datetime, timedelta

            # 最近7天创建的Token数量
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_tokens_count = db.session.query(func.count(Asset.id)).filter(
                Asset.spl_created_at >= seven_days_ago,
                Asset.spl_mint_address.isnot(None)
            ).scalar() or 0

            # 最近失败的Token创建数量
            recent_failed_count = db.session.query(func.count(Asset.id)).filter(
                Asset.spl_creation_status == SplTokenService.CreationStatus.FAILED,
                Asset.updated_at >= seven_days_ago
            ).scalar() or 0

            dashboard_data['recent_activity'] = {
                'tokens_created_7_days': recent_tokens_count,
                'failed_creations_7_days': recent_failed_count
            }

        except Exception as e:
            logger.warning(f"获取额外仪表板数据失败: {e}")
            dashboard_data['recent_activity'] = {
                'tokens_created_7_days': 0,
                'failed_creations_7_days': 0
            }

        return success_response(
            data=dashboard_data,
            message="获取仪表板统计信息成功"
        )

    except Exception as e:
        logger.error(f"获取仪表板统计信息API异常: {e}", exc_info=True)
        return error_response(message=f"获取仪表板统计信息失败: {str(e)}")


@spl_token_bp.route('/api/spl-token/health-check/<mint_address>', methods=['GET'])
def token_health_check(mint_address):
    """Token健康检查"""
    try:
        logger.info(f"执行Token健康检查: {mint_address}")

        health_data = {
            'mint_address': mint_address,
            'timestamp': time.time(),
            'checks': {}
        }

        # 检查1: Mint账户是否存在
        try:
            from app.blockchain.solana_service import get_solana_client
            from solders.pubkey import Pubkey

            client = get_solana_client()
            mint_pubkey = Pubkey.from_string(mint_address)
            mint_info = client.get_account_info(mint_pubkey)

            health_data['checks']['mint_account_exists'] = {
                'status': 'pass' if mint_info.value else 'fail',
                'message': 'Mint账户存在' if mint_info.value else 'Mint账户不存在'
            }
        except Exception as e:
            health_data['checks']['mint_account_exists'] = {
                'status': 'error',
                'message': f'检查Mint账户失败: {str(e)}'
            }

        # 检查2: 数据库记录是否存在
        try:
            asset = Asset.query.filter_by(spl_mint_address=mint_address).first()
            health_data['checks']['database_record'] = {
                'status': 'pass' if asset else 'fail',
                'message': '数据库记录存在' if asset else '数据库记录不存在',
                'asset_id': asset.id if asset else None
            }
        except Exception as e:
            health_data['checks']['database_record'] = {
                'status': 'error',
                'message': f'检查数据库记录失败: {str(e)}'
            }

        # 检查3: 供应量信息
        supply_result = SplTokenService.get_token_supply_info(mint_address)
        health_data['checks']['supply_info'] = {
            'status': 'pass' if supply_result.get('success') else 'fail',
            'message': '供应量信息正常' if supply_result.get('success') else supply_result.get('message', '获取供应量失败'),
            'data': supply_result.get('data') if supply_result.get('success') else None
        }

        # 计算总体健康状态
        all_checks = health_data['checks'].values()
        passed_checks = sum(1 for check in all_checks if check['status'] == 'pass')
        total_checks = len(all_checks)

        health_data['overall_status'] = {
            'status': 'healthy' if passed_checks == total_checks else 'degraded' if passed_checks > 0 else 'unhealthy',
            'passed_checks': passed_checks,
            'total_checks': total_checks,
            'health_score': round((passed_checks / total_checks) * 100, 2) if total_checks > 0 else 0
        }

        return success_response(
            data=health_data,
            message="健康检查完成"
        )

    except Exception as e:
        logger.error(f"Token健康检查API异常: {e}", exc_info=True)
        return error_response(message=f"健康检查失败: {str(e)}")
