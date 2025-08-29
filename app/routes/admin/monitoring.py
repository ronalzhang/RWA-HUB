"""
Admin monitoring routes for transaction and blockchain health monitoring.
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required

from app.services.transaction_monitor import transaction_monitor
from app.services.dashboard_monitor import dashboard_monitor
from app.services.log_aggregator import transaction_log_aggregator
from app.utils.decorators import admin_required

logger = logging.getLogger(__name__)

monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/admin/monitoring')


@monitoring_bp.route('/dashboard')
@login_required
@admin_required
def monitoring_dashboard():
    """Render the monitoring dashboard page"""
    return render_template('admin_v2/monitoring_dashboard.html')


@monitoring_bp.route('/api/transaction-health')
@login_required
@admin_required
def get_transaction_health():
    """Get transaction health summary for dashboard"""
    try:
        health_summary = dashboard_monitor.get_transaction_health_summary()
        return jsonify({
            'success': True,
            'data': health_summary
        })
    except Exception as e:
        logger.error(f"Error getting transaction health: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/blockchain-health')
@login_required
@admin_required
def get_blockchain_health():
    """Get blockchain connection health summary"""
    try:
        health_summary = dashboard_monitor.get_blockchain_health_summary()
        return jsonify({
            'success': True,
            'data': health_summary
        })
    except Exception as e:
        logger.error(f"Error getting blockchain health: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/performance-metrics')
@login_required
@admin_required
def get_performance_metrics():
    """Get performance metrics for dashboard"""
    try:
        performance_metrics = dashboard_monitor.get_performance_metrics()
        return jsonify({
            'success': True,
            'data': performance_metrics
        })
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/alerts')
@login_required
@admin_required
def get_alerts():
    """Get current alerts for dashboard"""
    try:
        alerts = dashboard_monitor.get_dashboard_alerts()
        return jsonify({
            'success': True,
            'data': alerts
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/error-analysis')
@login_required
@admin_required
def get_error_analysis():
    """Get detailed error analysis"""
    hours = request.args.get('hours', 24, type=int)
    
    try:
        error_analysis = dashboard_monitor.get_error_analysis(hours=hours)
        return jsonify({
            'success': True,
            'data': error_analysis
        })
    except Exception as e:
        logger.error(f"Error getting error analysis: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/transaction-metrics')
@login_required
@admin_required
def get_transaction_metrics():
    """Get detailed transaction metrics"""
    hours = request.args.get('hours', 24, type=int)
    
    try:
        metrics = transaction_monitor.get_transaction_metrics(hours=hours)
        return jsonify({
            'success': True,
            'data': metrics
        })
    except Exception as e:
        logger.error(f"Error getting transaction metrics: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/blockchain-status')
@login_required
@admin_required
def get_blockchain_status():
    """Get detailed blockchain connection status"""
    try:
        status = transaction_monitor.get_blockchain_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting blockchain status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/logs/search')
@login_required
@admin_required
def search_logs():
    """Search transaction-related logs"""
    query = request.args.get('query', '')
    hours = request.args.get('hours', 24, type=int)
    trade_id = request.args.get('trade_id', type=int)
    error_type = request.args.get('error_type')
    
    try:
        logs = transaction_log_aggregator.search_logs(
            query=query,
            hours=hours,
            trade_id=trade_id,
            error_type=error_type
        )
        return jsonify({
            'success': True,
            'data': logs
        })
    except Exception as e:
        logger.error(f"Error searching logs: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/logs/critical')
@login_required
@admin_required
def get_critical_errors():
    """Get critical errors that need immediate attention"""
    hours = request.args.get('hours', 24, type=int)
    
    try:
        critical_errors = transaction_log_aggregator.get_critical_errors(hours=hours)
        return jsonify({
            'success': True,
            'data': critical_errors
        })
    except Exception as e:
        logger.error(f"Error getting critical errors: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/logs/summary')
@login_required
@admin_required
def get_log_summary():
    """Get transaction error log summary"""
    hours = request.args.get('hours', 24, type=int)
    
    try:
        summary = transaction_log_aggregator.get_transaction_error_summary(hours=hours)
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        logger.error(f"Error getting log summary: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/logs/trends')
@login_required
@admin_required
def get_error_trends():
    """Get error trends over time"""
    days = request.args.get('days', 7, type=int)
    
    try:
        trends = transaction_log_aggregator.get_error_trends(days=days)
        return jsonify({
            'success': True,
            'data': trends
        })
    except Exception as e:
        logger.error(f"Error getting error trends: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/logs/export')
@login_required
@admin_required
def export_logs():
    """Export logs in specified format"""
    hours = request.args.get('hours', 24, type=int)
    format_type = request.args.get('format', 'json')
    transaction_only = request.args.get('transaction_only', 'true').lower() == 'true'
    
    try:
        exported_data = transaction_log_aggregator.export_logs(
            hours=hours,
            format=format_type,
            transaction_only=transaction_only
        )
        
        if format_type.lower() == 'csv':
            response = jsonify({
                'success': True,
                'data': exported_data,
                'content_type': 'text/csv'
            })
        else:
            response = jsonify({
                'success': True,
                'data': exported_data,
                'content_type': 'application/json'
            })
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting logs: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/health-check')
@login_required
@admin_required
def health_check():
    """Overall system health check"""
    try:
        # Get current status from all monitoring components
        transaction_health = dashboard_monitor.get_transaction_health_summary()
        blockchain_health = dashboard_monitor.get_blockchain_health_summary()
        performance_metrics = dashboard_monitor.get_performance_metrics()
        alerts = dashboard_monitor.get_dashboard_alerts()
        
        # Determine overall system health
        critical_alerts = [alert for alert in alerts if alert['level'] == 'critical']
        warning_alerts = [alert for alert in alerts if alert['level'] == 'warning']
        
        if critical_alerts:
            overall_status = 'critical'
        elif warning_alerts or transaction_health['overall_status'] != 'healthy' or blockchain_health['overall_status'] != 'healthy':
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        return jsonify({
            'success': True,
            'data': {
                'overall_status': overall_status,
                'timestamp': datetime.utcnow().isoformat(),
                'components': {
                    'transactions': transaction_health['overall_status'],
                    'blockchain': blockchain_health['overall_status'],
                    'performance': 'healthy'  # Could add performance thresholds
                },
                'alerts': {
                    'critical': len(critical_alerts),
                    'warning': len(warning_alerts),
                    'total': len(alerts)
                },
                'metrics': {
                    'transaction_success_rate_24h': transaction_health['last_24_hours']['success_rate'],
                    'blockchain_response_time_ms': blockchain_health['connection_status']['average_response_time_ms'],
                    'transaction_throughput_24h': performance_metrics['transaction_throughput_24h']
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'overall_status': 'critical'
        }), 500