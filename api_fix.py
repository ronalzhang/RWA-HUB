@api_bp.route('/user/assets', methods=['GET'])
def get_user_assets_query():
    """获取用户持有的资产数据（通过查询参数）"""
    try:
        # 从查询参数获取地址和钱包类型
        address = request.args.get('address')
        wallet_type = request.args.get('wallet_type', 'ethereum')
        
        if not address:
            return jsonify({'success': False, 'error': '缺少钱包地址'}), 400
            
        # 记录当前请求的钱包地址，用于调试
        current_app.logger.info(f'通过查询参数获取资产 - 地址: {address}, 类型: {wallet_type}')
        
        # 添加查询资产的逻辑
        from app.models.asset import Asset
        from app.models.holding import Holding
        from app.models.user import User
        from sqlalchemy import or_
        
        # 查询用户
        user = None
        try:
            # 尝试查找用户 - 兼容不同地址大小写
            if address.startswith('0x'):  # 以太坊地址
                # 查询用户 - 同时匹配原始大小写和小写地址
                user = User.query.filter(
                    or_(
                        User.eth_address == address,
                        User.eth_address == address.lower()
                    )
                ).first()
            else:  # Solana地址
                user = User.query.filter_by(sol_address=address).first()
        except Exception as e:
            current_app.logger.error(f'查询用户失败: {str(e)}')
            
        # 如果找不到用户，返回空数组
        if not user:
            current_app.logger.info(f'未找到用户: {address}，返回空数组')
            return jsonify([]), 200
            
        current_app.logger.info(f'找到用户 ID: {user.id}，查询其资产')
        
        # 查询用户持有的资产
        holdings = Holding.query.filter_by(user_id=user.id).all()
        
        # 如果没有持有资产，返回空数组
        if not holdings:
            current_app.logger.info(f'用户 {user.id} 没有持有资产，返回空数组')
            return jsonify([]), 200
            
        # 准备返回的资产数据
        result = []
        
        for holding in holdings:
            # 查询资产详情
            asset = Asset.query.get(holding.asset_id)
            if not asset:
                continue
                
            # 构建资产数据
            asset_data = {
                'asset_id': asset.id,
                'name': asset.name,
                'symbol': asset.symbol,
                'quantity': holding.quantity,
                'price': asset.current_price
            }
            result.append(asset_data)
            
        current_app.logger.info(f'返回用户 {user.id} 的 {len(result)} 个资产')
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f'获取用户资产失败: {str(e)}', exc_info=True)
        return jsonify([]), 200 