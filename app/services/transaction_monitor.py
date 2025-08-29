"""
Transaction monitoring service for tracking success/failure rates and alerting.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import json

from app.extensions import db
from app.models.trade import Trade
from app.utils.error_handler import ErrorHandler


class TransactionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class TransactionMetric:
    """Transaction metric data structure"""
    timestamp: datetime
    status: TransactionStatus
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    trade_id: Optional[int] = None


@dataclass
class Alert:
    """Alert data structure"""
    level: AlertLevel
    message: str
    timestamp: datetime
    metric_type: str
    details: Dict[str, Any]


class TransactionMonitor:
    """
    Monitors transaction creation success/failure rates and generates alerts
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler()
        
        # In-memory storage for recent metrics (last 24 hours)
        self.recent_metrics: deque = deque(maxlen=10000)
        
        # Failure tracking for alerting
        self.failure_counts = defaultdict(int)
        self.last_alert_time = defaultdict(float)
        
        # Configuration
        self.alert_thresholds = {
            'failure_rate_warning': 0.1,  # 10% failure rate
            'failure_rate_critical': 0.25,  # 25% failure rate
            'consecutive_failures_warning': 5,
            'consecutive_failures_critical': 10,
            'blockchain_connection_timeout': 30,  # seconds
            'alert_cooldown': 300  # 5 minutes between similar alerts
        }
        
        # Blockchain connection monitoring
        self.blockchain_status = {
            'last_successful_connection': None,
            'connection_failures': 0,
            'rpc_response_times': deque(maxlen=100)
        }
    
    def record_transaction_attempt(self, 
                                 status: TransactionStatus,
                                 trade_id: Optional[int] = None,
                                 error_type: Optional[str] = None,
                                 error_message: Optional[str] = None,
                                 duration_ms: Optional[int] = None) -> None:
        """Record a transaction creation attempt"""
        
        metric = TransactionMetric(
            timestamp=datetime.utcnow(),
            status=status,
            error_type=error_type,
            error_message=error_message,
            duration_ms=duration_ms,
            trade_id=trade_id
        )
        
        self.recent_metrics.append(metric)
        
        # Log the metric
        self.logger.info(f"Transaction attempt recorded: {status.value}", extra={
            'trade_id': trade_id,
            'error_type': error_type,
            'duration_ms': duration_ms
        })
        
        # Check for alerts
        self._check_failure_rate_alerts()
        self._check_consecutive_failure_alerts()
        
        # Update failure counts for alerting
        if status == TransactionStatus.FAILED:
            self.failure_counts[error_type or 'unknown'] += 1
        
    def record_blockchain_connection(self, 
                                   success: bool, 
                                   response_time_ms: Optional[int] = None,
                                   error_message: Optional[str] = None) -> None:
        """Record blockchain connection attempt"""
        
        if success:
            self.blockchain_status['last_successful_connection'] = datetime.utcnow()
            self.blockchain_status['connection_failures'] = 0
            if response_time_ms:
                self.blockchain_status['rpc_response_times'].append(response_time_ms)
        else:
            self.blockchain_status['connection_failures'] += 1
            self.logger.warning(f"Blockchain connection failed: {error_message}")
            
            # Check for blockchain connection alerts
            self._check_blockchain_connection_alerts()
    
    def get_transaction_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get transaction metrics for the specified time period"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [m for m in self.recent_metrics if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {
                'total_attempts': 0,
                'success_rate': 0.0,
                'failure_rate': 0.0,
                'average_duration_ms': 0,
                'error_breakdown': {}
            }
        
        total_attempts = len(recent_metrics)
        successful = sum(1 for m in recent_metrics if m.status == TransactionStatus.SUCCESS)
        failed = sum(1 for m in recent_metrics if m.status == TransactionStatus.FAILED)
        
        # Calculate durations for successful transactions
        durations = [m.duration_ms for m in recent_metrics 
                    if m.duration_ms and m.status == TransactionStatus.SUCCESS]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Error breakdown
        error_breakdown = defaultdict(int)
        for metric in recent_metrics:
            if metric.status == TransactionStatus.FAILED and metric.error_type:
                error_breakdown[metric.error_type] += 1
        
        return {
            'total_attempts': total_attempts,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total_attempts if total_attempts > 0 else 0,
            'failure_rate': failed / total_attempts if total_attempts > 0 else 0,
            'average_duration_ms': avg_duration,
            'error_breakdown': dict(error_breakdown),
            'time_period_hours': hours
        }
    
    def get_blockchain_status(self) -> Dict[str, Any]:
        """Get current blockchain connection status"""
        
        response_times = list(self.blockchain_status['rpc_response_times'])
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        last_connection = self.blockchain_status['last_successful_connection']
        connection_age_seconds = None
        if last_connection:
            connection_age_seconds = (datetime.utcnow() - last_connection).total_seconds()
        
        return {
            'last_successful_connection': last_connection.isoformat() if last_connection else None,
            'connection_age_seconds': connection_age_seconds,
            'consecutive_failures': self.blockchain_status['connection_failures'],
            'average_response_time_ms': avg_response_time,
            'recent_response_times': response_times[-10:],  # Last 10 response times
            'is_healthy': (
                connection_age_seconds is not None and 
                connection_age_seconds < self.alert_thresholds['blockchain_connection_timeout'] and
                self.blockchain_status['connection_failures'] < 3
            )
        }
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts (this would typically be stored in database)"""
        # For now, return empty list - in production this would query a database
        # or external monitoring system
        return []
    
    def _check_failure_rate_alerts(self) -> None:
        """Check if failure rate exceeds thresholds and generate alerts"""
        
        metrics = self.get_transaction_metrics(hours=1)  # Check last hour
        
        if metrics['total_attempts'] < 5:  # Need minimum attempts for meaningful rate
            return
        
        failure_rate = metrics['failure_rate']
        
        # Critical alert
        if failure_rate >= self.alert_thresholds['failure_rate_critical']:
            self._generate_alert(
                AlertLevel.CRITICAL,
                f"Critical transaction failure rate: {failure_rate:.1%} in last hour",
                'failure_rate',
                {'failure_rate': failure_rate, 'total_attempts': metrics['total_attempts']}
            )
        # Warning alert
        elif failure_rate >= self.alert_thresholds['failure_rate_warning']:
            self._generate_alert(
                AlertLevel.WARNING,
                f"High transaction failure rate: {failure_rate:.1%} in last hour",
                'failure_rate',
                {'failure_rate': failure_rate, 'total_attempts': metrics['total_attempts']}
            )
    
    def _check_consecutive_failure_alerts(self) -> None:
        """Check for consecutive failures and generate alerts"""
        
        if len(self.recent_metrics) < 5:
            return
        
        # Check last 10 transactions for consecutive failures
        recent_statuses = [m.status for m in list(self.recent_metrics)[-10:]]
        consecutive_failures = 0
        
        for status in reversed(recent_statuses):
            if status == TransactionStatus.FAILED:
                consecutive_failures += 1
            else:
                break
        
        # Critical alert
        if consecutive_failures >= self.alert_thresholds['consecutive_failures_critical']:
            self._generate_alert(
                AlertLevel.CRITICAL,
                f"Critical: {consecutive_failures} consecutive transaction failures",
                'consecutive_failures',
                {'consecutive_failures': consecutive_failures}
            )
        # Warning alert
        elif consecutive_failures >= self.alert_thresholds['consecutive_failures_warning']:
            self._generate_alert(
                AlertLevel.WARNING,
                f"Warning: {consecutive_failures} consecutive transaction failures",
                'consecutive_failures',
                {'consecutive_failures': consecutive_failures}
            )
    
    def _check_blockchain_connection_alerts(self) -> None:
        """Check blockchain connection health and generate alerts"""
        
        failures = self.blockchain_status['connection_failures']
        last_success = self.blockchain_status['last_successful_connection']
        
        # Check if too much time has passed since last successful connection
        if last_success:
            time_since_success = (datetime.utcnow() - last_success).total_seconds()
            if time_since_success > self.alert_thresholds['blockchain_connection_timeout']:
                self._generate_alert(
                    AlertLevel.CRITICAL,
                    f"Blockchain connection down for {time_since_success:.0f} seconds",
                    'blockchain_connection',
                    {'time_since_success': time_since_success, 'consecutive_failures': failures}
                )
        
        # Check consecutive failures
        if failures >= 5:
            self._generate_alert(
                AlertLevel.CRITICAL,
                f"Blockchain connection: {failures} consecutive failures",
                'blockchain_connection',
                {'consecutive_failures': failures}
            )
    
    def _generate_alert(self, 
                       level: AlertLevel, 
                       message: str, 
                       metric_type: str, 
                       details: Dict[str, Any]) -> None:
        """Generate and log an alert"""
        
        # Check cooldown to avoid spam
        alert_key = f"{level.value}_{metric_type}"
        current_time = time.time()
        
        if (current_time - self.last_alert_time[alert_key]) < self.alert_thresholds['alert_cooldown']:
            return
        
        self.last_alert_time[alert_key] = current_time
        
        alert = Alert(
            level=level,
            message=message,
            timestamp=datetime.utcnow(),
            metric_type=metric_type,
            details=details
        )
        
        # Log the alert
        log_level = logging.CRITICAL if level == AlertLevel.CRITICAL else logging.WARNING
        self.logger.log(log_level, f"ALERT [{level.value.upper()}]: {message}", extra={
            'alert_type': metric_type,
            'alert_details': details
        })
        
        # In production, this would also:
        # - Send notifications (email, Slack, etc.)
        # - Store in database for dashboard
        # - Trigger automated responses if configured


# Global instance
transaction_monitor = TransactionMonitor()