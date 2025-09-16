from flask import Blueprint, request, jsonify
from flask_limiter.util import get_remote_address
import logging

from app.models import Asset
from app.services.spl_token_service import SplTokenService
from app.utils.response_helpers import success_response, error_response
from app.extensions import limiter

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