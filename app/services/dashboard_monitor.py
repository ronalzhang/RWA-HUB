"""
Dashboard monitoring service for blockchain and transaction health.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import json

from app.services.transaction_monitor import transaction_monitor, TransactionStatus
from app.extensions import db
from app.models.trade import Trade


@dataclass
class HealthMetric:
    """Health metric for dashboard display"""
    name: str
    value: Any
    status: str  # 'healthy', 'warning', 'critical'
    description: str
    last_updated: datetime


class DashboardMonitor:
    """
    Provides monitoring data for admin dashboard
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_transaction_health_summary(self) -> Dict[str, Any]:
        """Get overall transaction health summary for dashboard"""
        
        # Get metrics for different time periods
        metrics_1h = transaction_monitor.get_transaction_metrics(hours=1)
        metrics_24h = transaction_monitor.get_transaction_metrics(hours=24)
        metrics_7d = transaction_monitor.get_transaction_metrics(hours=168)
        
        # Determine overall health status
        health_status = self._determine_transaction_health_status(metrics_1h, metrics_24h)
        
        return {
            'overall_status': health_status,
            'last_hour': metrics_1h,
            'last_24_hours': metrics_24h,
            'last_7_days': metrics_7d,
            'health_indicators': self._get_transaction_health_indicators(metrics_1h, metrics_24h)
        }
    
    def get_blockchain_health_summary(self) -> Dict[str, Any]:
        """Get blockchain connection health summary"""
        
        blockchain_status = transaction_monitor.get_blockchain_status()
        
        # Determine health status
        if blockchain_status['is_healthy']:
            health_status = 'healthy'
        elif blockchain_status['consecutive_failures'] < 5:
            health_status = 'warning'
        else:
            health_status = 'critical'
        
        return {
            'overall_status': health_status,
            'connection_status': blockchain_status,
            'health_indicators': self._get_blockchain_health_indicators(blockchain_status)
        }
    
    def get_error_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """Get detailed error analysis for troubleshooting"""
        
        metrics = transaction_monitor.get_transaction_metrics(hours=hours)
        
        # Get database trade errors for comparison
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        try:
            failed_trades = db.session.query(Trade).filter(
                Trade.created_at >= cutoff_time,
                Trade.status.in_(['failed', 'error'])
            ).all()
            
            db_error_breakdown = {}
            for trade in failed_trades:
                error_type = getattr(trade, 'error_message', 'unknown')[:50]  # First 50 chars
                db_error_breakdown[error_type] = db_error_breakdown.get(error_type, 0) + 1
                
        except Exception as e:
            self.logger.error(f"Error querying failed trades: {e}")
            db_error_breakdown = {}
        
        return {
            'time_period_hours': hours,
            'monitor_errors': metrics['error_breakdown'],
            'database_errors': db_error_breakdown,
            'total_monitor_failures': sum(metrics['error_breakdown'].values()),
            'total_db_failures': len(failed_trades) if 'failed_trades' in locals() else 0,
            'common_error_patterns': self._analyze_error_patterns(metrics['error_breakdown'])
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for dashboard"""
        
        blockchain_status = transaction_monitor.get_blockchain_status()
        transaction_metrics = transaction_monitor.get_transaction_metrics(hours=24)
        
        return {
            'average_transaction_duration_ms': transaction_metrics['average_duration_ms'],
            'average_rpc_response_time_ms': blockchain_status['average_response_time_ms'],
            'transaction_throughput_24h': transaction_metrics['total_attempts'],
            'success_rate_24h': transaction_metrics['success_rate'],
            'performance_indicators': self._get_performance_indicators(
                transaction_metrics, blockchain_status
            )
        }
    
    def get_dashboard_alerts(self) -> List[Dict[str, Any]]:
        """Get current alerts for dashboard display"""
        
        alerts = []
        
        # Transaction health alerts
        metrics_1h = transaction_monitor.get_transaction_metrics(hours=1)
        if metrics_1h['total_attempts'] > 0:
            if metrics_1h['failure_rate'] >= 0.25:
                alerts.append({
                    'level': 'critical',
                    'type': 'transaction_failure_rate',
                    'message': f"Critical transaction failure rate: {metrics_1h['failure_rate']:.1%}",
                    'timestamp': datetime.utcnow().isoformat(),
                    'details': metrics_1h
                })
            elif metrics_1h['failure_rate'] >= 0.1:
                alerts.append({
                    'level': 'warning',
                    'type': 'transaction_failure_rate',
                    'message': f"High transaction failure rate: {metrics_1h['failure_rate']:.1%}",
                    'timestamp': datetime.utcnow().isoformat(),
                    'details': metrics_1h
                })
        
        # Blockchain connection alerts
        blockchain_status = transaction_monitor.get_blockchain_status()
        if not blockchain_status['is_healthy']:
            level = 'critical' if blockchain_status['consecutive_failures'] >= 5 else 'warning'
            alerts.append({
                'level': level,
                'type': 'blockchain_connection',
                'message': f"Blockchain connection issues: {blockchain_status['consecutive_failures']} failures",
                'timestamp': datetime.utcnow().isoformat(),
                'details': blockchain_status
            })
        
        return alerts
    
    def _determine_transaction_health_status(self, metrics_1h: Dict, metrics_24h: Dict) -> str:
        """Determine overall transaction health status"""
        
        # Check recent activity first
        if metrics_1h['total_attempts'] > 0:
            if metrics_1h['failure_rate'] >= 0.25:
                return 'critical'
            elif metrics_1h['failure_rate'] >= 0.1:
                return 'warning'
        
        # Check 24h trends
        if metrics_24h['total_attempts'] > 0:
            if metrics_24h['failure_rate'] >= 0.15:
                return 'warning'
        
        return 'healthy'
    
    def _get_transaction_health_indicators(self, metrics_1h: Dict, metrics_24h: Dict) -> List[HealthMetric]:
        """Get transaction health indicators"""
        
        indicators = []
        
        # Success rate indicator
        success_rate = metrics_24h['success_rate']
        if success_rate >= 0.95:
            status = 'healthy'
        elif success_rate >= 0.85:
            status = 'warning'
        else:
            status = 'critical'
        
        indicators.append(HealthMetric(
            name='Transaction Success Rate (24h)',
            value=f"{success_rate:.1%}",
            status=status,
            description=f"Success rate over last 24 hours ({metrics_24h['total_attempts']} attempts)",
            last_updated=datetime.utcnow()
        ))
        
        # Recent failure rate
        recent_failure_rate = metrics_1h['failure_rate']
        if recent_failure_rate == 0:
            status = 'healthy'
        elif recent_failure_rate < 0.1:
            status = 'warning'
        else:
            status = 'critical'
        
        indicators.append(HealthMetric(
            name='Recent Failure Rate (1h)',
            value=f"{recent_failure_rate:.1%}",
            status=status,
            description=f"Failure rate in last hour ({metrics_1h['total_attempts']} attempts)",
            last_updated=datetime.utcnow()
        ))
        
        return [asdict(indicator) for indicator in indicators]
    
    def _get_blockchain_health_indicators(self, blockchain_status: Dict) -> List[HealthMetric]:
        """Get blockchain health indicators"""
        
        indicators = []
        
        # Connection status
        if blockchain_status['is_healthy']:
            status = 'healthy'
            description = 'Blockchain connection is healthy'
        elif blockchain_status['consecutive_failures'] < 5:
            status = 'warning'
            description = f"{blockchain_status['consecutive_failures']} recent connection failures"
        else:
            status = 'critical'
            description = f"{blockchain_status['consecutive_failures']} consecutive connection failures"
        
        indicators.append(HealthMetric(
            name='Blockchain Connection',
            value='Connected' if blockchain_status['is_healthy'] else 'Issues',
            status=status,
            description=description,
            last_updated=datetime.utcnow()
        ))
        
        # Response time
        avg_response_time = blockchain_status['average_response_time_ms']
        if avg_response_time == 0:
            status = 'warning'
            value = 'No data'
        elif avg_response_time < 1000:
            status = 'healthy'
            value = f"{avg_response_time:.0f}ms"
        elif avg_response_time < 3000:
            status = 'warning'
            value = f"{avg_response_time:.0f}ms"
        else:
            status = 'critical'
            value = f"{avg_response_time:.0f}ms"
        
        indicators.append(HealthMetric(
            name='RPC Response Time',
            value=value,
            status=status,
            description='Average response time for blockchain RPC calls',
            last_updated=datetime.utcnow()
        ))
        
        return [asdict(indicator) for indicator in indicators]
    
    def _get_performance_indicators(self, transaction_metrics: Dict, blockchain_status: Dict) -> List[HealthMetric]:
        """Get performance indicators"""
        
        indicators = []
        
        # Transaction throughput
        throughput = transaction_metrics['total_attempts']
        if throughput >= 100:
            status = 'healthy'
        elif throughput >= 10:
            status = 'warning'
        else:
            status = 'critical' if throughput == 0 else 'warning'
        
        indicators.append(HealthMetric(
            name='Transaction Throughput (24h)',
            value=str(throughput),
            status=status,
            description='Total transaction attempts in last 24 hours',
            last_updated=datetime.utcnow()
        ))
        
        return [asdict(indicator) for indicator in indicators]
    
    def _analyze_error_patterns(self, error_breakdown: Dict[str, int]) -> List[Dict[str, Any]]:
        """Analyze error patterns to identify common issues"""
        
        if not error_breakdown:
            return []
        
        total_errors = sum(error_breakdown.values())
        patterns = []
        
        for error_type, count in sorted(error_breakdown.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_errors) * 100
            
            # Categorize error types
            category = 'unknown'
            if 'configuration' in error_type.lower():
                category = 'configuration'
            elif 'blockchain' in error_type.lower() or 'rpc' in error_type.lower():
                category = 'blockchain'
            elif 'serialization' in error_type.lower():
                category = 'serialization'
            elif 'validation' in error_type.lower():
                category = 'validation'
            
            patterns.append({
                'error_type': error_type,
                'count': count,
                'percentage': percentage,
                'category': category
            })
        
        return patterns[:10]  # Return top 10 patterns


# Global instance
dashboard_monitor = DashboardMonitor()