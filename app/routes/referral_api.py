"""
推荐系统API路由
提供推荐系统相关的API接口
"""

from flask import Blueprint, request, jsonify, current_app
from decimal import Decimal
import logging

from app.services.unlimited_referral_system import UnlimitedReferralSystem
from app.services.auto_commission_service import AutoCommissionService
from app.services.referral_link_generator import ReferralLinkGenerator
from app.services.referral_visualization import ReferralVisualization

logger = logging.getLogger(__name__)

# 创建蓝图
referral_bp = Blueprint('referral_api', __name__, url_prefix='/api/referral')

# 初始化服务
referral_system = UnlimitedReferralSystem()
commission_service = AutoCommissionService()
link_generator = ReferralLinkGenerator()
visualization = ReferralVisualization()


@referral_bp.route('/register', methods=['POST'])
def register_referral():
    """注册推荐关系"""
    try:
        data = request.get_json()
        user_address = data.get('user_address')
        referrer_address = data.get('referrer_address')
        referral_code = data.get('referral_code')
        
        if not user_address or not referrer_address:
            return jsonify({
                'success': False,
                'error': '用户地址和推荐人地址不能为空'
            }), 400
        
        # 注册推荐关系
        referral = referral_system.register_referral(
            user_address=user_address,
            referrer_address=referrer_address,
            referral_code=referral_code
        )
        
        return jsonify({
            'success': True,
            'data': referral.to_dict(),
            'message': '推荐关系注册成功'
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"注册推荐关系失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/generate-link', methods=['POST'])
def generate_referral_link():
    """生成推荐链接"""
    try:
        data = request.get_json()
        referrer_address = data.get('referrer_address')
        custom_code = data.get('custom_code')
        expiry_days = data.get('expiry_days')
        campaign = data.get('campaign')
        
        if not referrer_address:
            return jsonify({
                'success': False,
                'error': '推荐人地址不能为空'
            }), 400
        
        # 生成推荐链接
        link_info = link_generator.generate_referral_link(
            referrer_address=referrer_address,
            custom_code=custom_code,
            expiry_days=expiry_days,
            campaign=campaign
        )
        
        return jsonify({
            'success': True,
            'data': link_info,
            'message': '推荐链接生成成功'
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"生成推荐链接失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/statistics/<address>', methods=['GET'])
def get_referral_statistics(address):
    """获取推荐统计"""
    try:
        stats = referral_system.get_referral_statistics(address)
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': '获取推荐统计成功'
        })
        
    except Exception as e:
        logger.error(f"获取推荐统计失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/commission/calculate', methods=['POST'])
def calculate_commission():
    """计算佣金分配"""
    try:
        data = request.get_json()
        transaction_amount = data.get('transaction_amount')
        user_address = data.get('user_address')
        
        if not transaction_amount or not user_address:
            return jsonify({
                'success': False,
                'error': '交易金额和用户地址不能为空'
            }), 400
        
        # 计算佣金分配
        distribution = referral_system.calculate_commission_distribution(
            Decimal(str(transaction_amount)),
            user_address
        )
        
        # 转换Decimal为float以便JSON序列化
        for commission in distribution['referral_commissions']:
            commission['commission_amount'] = float(commission['commission_amount'])
            commission['rate'] = float(commission['rate'])
        
        distribution['platform_fee'] = float(distribution['platform_fee'])
        distribution['total_referral_amount'] = float(distribution['total_referral_amount'])
        
        return jsonify({
            'success': True,
            'data': distribution,
            'message': '佣金分配计算成功'
        })
        
    except Exception as e:
        logger.error(f"计算佣金分配失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/link/statistics/<address>', methods=['GET'])
def get_link_statistics(address):
    """获取链接统计"""
    try:
        stats = link_generator.get_link_statistics(address)
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': '获取链接统计成功'
        })
        
    except Exception as e:
        logger.error(f"获取链接统计失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/link/track/<referral_code>', methods=['POST'])
def track_link_click(referral_code):
    """跟踪链接点击"""
    try:
        visitor_info = {
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'timestamp': request.json.get('timestamp') if request.json else None
        }
        
        result = link_generator.track_link_click(referral_code, visitor_info)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"跟踪链接点击失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/platform/sustainability', methods=['GET'])
def get_platform_sustainability():
    """获取平台可持续性指标"""
    try:
        metrics = commission_service.get_platform_sustainability_metrics()
        
        return jsonify({
            'success': True,
            'data': metrics,
            'message': '获取平台可持续性指标成功'
        })
        
    except Exception as e:
        logger.error(f"获取平台可持续性指标失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/visualization/network/<address>', methods=['GET'])
def get_network_visualization(address):
    """获取网络可视化数据"""
    try:
        max_depth = request.args.get('max_depth', 5, type=int)
        
        network_data = visualization.generate_network_graph(address, max_depth)
        
        return jsonify({
            'success': True,
            'data': network_data,
            'message': '获取网络可视化数据成功'
        })
        
    except Exception as e:
        logger.error(f"获取网络可视化数据失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/visualization/tree/<address>', methods=['GET'])
def get_tree_visualization(address):
    """获取树形可视化数据"""
    try:
        max_depth = request.args.get('max_depth', 5, type=int)
        
        tree_data = visualization.generate_hierarchy_tree(address, max_depth)
        
        return jsonify({
            'success': True,
            'data': tree_data,
            'message': '获取树形可视化数据成功'
        })
        
    except Exception as e:
        logger.error(f"获取树形可视化数据失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/commission/optimize', methods=['GET'])
def get_commission_optimization():
    """获取佣金优化建议"""
    try:
        optimization = commission_service.optimize_commission_rates()
        
        return jsonify({
            'success': True,
            'data': optimization,
            'message': '获取佣金优化建议成功'
        })
        
    except Exception as e:
        logger.error(f"获取佣金优化建议失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/system/integrity', methods=['GET'])
def check_system_integrity():
    """检查系统完整性"""
    try:
        integrity_result = referral_system.validate_referral_system_integrity()
        
        return jsonify({
            'success': True,
            'data': integrity_result,
            'message': '系统完整性检查完成'
        })
        
    except Exception as e:
        logger.error(f"系统完整性检查失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/batch/process-commissions', methods=['POST'])
def batch_process_commissions():
    """批量处理佣金"""
    try:
        data = request.get_json()
        trade_ids = data.get('trade_ids', [])
        
        if not trade_ids:
            return jsonify({
                'success': False,
                'error': '交易ID列表不能为空'
            }), 400
        
        # 批量处理佣金
        results = commission_service.process_batch_commission_records(trade_ids)
        
        # 转换Decimal为float
        results['total_commission_amount'] = float(results['total_commission_amount'])
        results['platform_earnings'] = float(results['platform_earnings'])
        
        return jsonify({
            'success': True,
            'data': results,
            'message': '批量佣金处理完成'
        })
        
    except Exception as e:
        logger.error(f"批量处理佣金失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


@referral_bp.route('/report/commission', methods=['GET'])
def generate_commission_report():
    """生成佣金报表"""
    try:
        from datetime import datetime, timedelta
        
        # 获取查询参数
        days = request.args.get('days', 30, type=int)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 生成报表
        report = commission_service.generate_commission_report(start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': report,
            'message': '佣金报表生成成功'
        })
        
    except Exception as e:
        logger.error(f"生成佣金报表失败: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500


# 错误处理
@referral_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'API接口不存在'
    }), 404


@referral_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'success': False,
        'error': 'HTTP方法不允许'
    }), 405


@referral_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500