"""
数据一致性验证器
确保资产数据完整性和一致性
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional
from ..models.asset import Asset, AssetStatus
from ..extensions import db
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """数据验证器类"""
    
    @staticmethod
    def validate_asset_data(asset: Asset) -> List[str]:
        """
        验证单个资产的数据一致性
        
        Args:
            asset: Asset实例
            
        Returns:
            List[str]: 问题列表，空列表表示无问题
        """
        issues = []
        
        # 检查基本字段
        if not asset.name or len(asset.name.strip()) == 0:
            issues.append(f"Asset {asset.id}: name is empty")
        
        if not asset.token_symbol or len(asset.token_symbol.strip()) == 0:
            issues.append(f"Asset {asset.id}: token_symbol is empty")
        
        # 检查数值字段
        if asset.token_supply is None or asset.token_supply <= 0:
            issues.append(f"Asset {asset.id}: invalid token_supply: {asset.token_supply}")
        
        if asset.token_price is None or asset.token_price <= 0:
            issues.append(f"Asset {asset.id}: invalid token_price: {asset.token_price}")
        
        # 检查剩余供应量
        if asset.remaining_supply is None:
            issues.append(f"Asset {asset.id}: remaining_supply is None")
        elif asset.remaining_supply < 0:
            issues.append(f"Asset {asset.id}: negative remaining_supply: {asset.remaining_supply}")
        elif asset.token_supply and asset.remaining_supply > asset.token_supply:
            issues.append(f"Asset {asset.id}: remaining_supply ({asset.remaining_supply}) > token_supply ({asset.token_supply})")
        
        # 检查售出比例计算
        if asset.token_supply and asset.remaining_supply is not None:
            sold = asset.token_supply - asset.remaining_supply
            sold_pct = (sold / asset.token_supply * 100) if asset.token_supply > 0 else 0
            
            if sold_pct < 0:
                issues.append(f"Asset {asset.id}: negative sold percentage: {sold_pct}%")
            elif sold_pct > 100:
                issues.append(f"Asset {asset.id}: sold percentage > 100%: {sold_pct}%")
        
        # 检查状态
        if asset.status not in [status.value for status in AssetStatus]:
            issues.append(f"Asset {asset.id}: invalid status: {asset.status}")
        
        return issues
    
    @staticmethod
    def validate_all_assets() -> Dict[str, Any]:
        """
        验证所有资产的数据一致性
        
        Returns:
            Dict: 验证结果汇总
        """
        try:
            assets = Asset.query.filter(Asset.deleted_at.is_(None)).all()
            
            all_issues = []
            asset_count = len(assets)
            valid_assets = 0
            
            for asset in assets:
                asset_issues = DataValidator.validate_asset_data(asset)
                if asset_issues:
                    all_issues.extend(asset_issues)
                else:
                    valid_assets += 1
            
            return {
                'success': True,
                'total_assets': asset_count,
                'valid_assets': valid_assets,
                'invalid_assets': asset_count - valid_assets,
                'total_issues': len(all_issues),
                'issues': all_issues
            }
            
        except Exception as e:
            logger.error(f"验证资产数据时出错: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def fix_asset_data_issues() -> Dict[str, Any]:
        """
        自动修复可修复的数据问题
        
        Returns:
            Dict: 修复结果汇总
        """
        try:
            assets = Asset.query.filter(Asset.deleted_at.is_(None)).all()
            fixed_count = 0
            fixes_applied = []
            
            for asset in assets:
                changes_made = False
                
                # 修复 remaining_supply = None 的问题
                if asset.remaining_supply is None and asset.token_supply:
                    asset.remaining_supply = asset.token_supply
                    fixes_applied.append(f"Asset {asset.id}: set remaining_supply = {asset.token_supply}")
                    changes_made = True
                
                # 修复负的 remaining_supply
                if asset.remaining_supply is not None and asset.remaining_supply < 0:
                    asset.remaining_supply = 0
                    fixes_applied.append(f"Asset {asset.id}: set remaining_supply = 0 (was negative)")
                    changes_made = True
                
                # 修复 remaining_supply > token_supply
                if (asset.remaining_supply is not None and asset.token_supply and 
                    asset.remaining_supply > asset.token_supply):
                    asset.remaining_supply = asset.token_supply
                    fixes_applied.append(f"Asset {asset.id}: set remaining_supply = {asset.token_supply} (was too high)")
                    changes_made = True
                
                if changes_made:
                    fixed_count += 1
            
            if fixed_count > 0:
                db.session.commit()
                logger.info(f"自动修复了 {fixed_count} 个资产的数据问题")
            
            return {
                'success': True,
                'fixed_assets': fixed_count,
                'fixes_applied': fixes_applied
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"修复资产数据时出错: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def ensure_asset_data_consistency(asset: Asset) -> bool:
        """
        确保单个资产数据的一致性（在保存前调用）
        
        Args:
            asset: Asset实例
            
        Returns:
            bool: True if data is consistent
        """
        try:
            # 自动修复可修复的问题
            if asset.remaining_supply is None and asset.token_supply:
                asset.remaining_supply = asset.token_supply
                logger.info(f"Auto-fixed remaining_supply for asset {asset.id}")
            
            if asset.remaining_supply is not None and asset.remaining_supply < 0:
                asset.remaining_supply = 0
                logger.info(f"Auto-fixed negative remaining_supply for asset {asset.id}")
            
            if (asset.remaining_supply is not None and asset.token_supply and 
                asset.remaining_supply > asset.token_supply):
                asset.remaining_supply = asset.token_supply
                logger.info(f"Auto-fixed excess remaining_supply for asset {asset.id}")
            
            # 验证修复后是否一致
            issues = DataValidator.validate_asset_data(asset)
            if issues:
                logger.warning(f"Asset {asset.id} still has issues after auto-fix: {issues}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"确保资产数据一致性时出错: {e}")
            return False