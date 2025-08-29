"""
Log aggregation service for transaction-related errors and monitoring.
"""
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
import re

from app.utils.error_handler import ErrorHandler


@dataclass
class LogEntry:
    """Structured log entry for aggregation"""
    timestamp: datetime
    level: str
    message: str
    logger_name: str
    trade_id: Optional[int] = None
    error_type: Optional[str] = None
    user_id: Optional[int] = None
    additional_data: Optional[Dict[str, Any]] = None


class TransactionLogAggregator:
    """
    Aggregates and analyzes transaction-related logs for monitoring and debugging
    """
    
    def __init__(self, log_file_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler()
        
        # Default log file path
        self.log_file_path = log_file_path or os.path.join('logs', 'app.log')
        
        # In-memory storage for recent logs
        self.recent_logs: deque = deque(maxlen=5000)
        
        # Error pattern tracking
        self.error_patterns = defaultdict(int)
        self.error_trends = defaultdict(list)
        
        # Transaction-specific log patterns
        self.transaction_patterns = [
            r'transaction.*creation.*failed',
            r'blockchain.*connection.*error',
            r'serialization.*error',
            r'configuration.*missing',
            r'rpc.*timeout',
            r'invalid.*transaction',
            r'wallet.*address.*invalid',
            r'insufficient.*balance',
            r'trade.*creation.*error'
        ]
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.transaction_patterns]
    
    def process_log_entry(self, 
                         level: str, 
                         message: str, 
                         logger_name: str = '',
                         extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Process a new log entry for aggregation"""
        
        # Extract transaction-related information
        trade_id = None
        error_type = None
        user_id = None
        
        if extra_data:
            trade_id = extra_data.get('trade_id')
            error_type = extra_data.get('error_type')
            user_id = extra_data.get('user_id')
        
        # Create log entry
        log_entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            message=message,
            logger_name=logger_name,
            trade_id=trade_id,
            error_type=error_type,
            user_id=user_id,
            additional_data=extra_data
        )
        
        # Store in recent logs
        self.recent_logs.append(log_entry)
        
        # Analyze for transaction-related patterns
        if self._is_transaction_related(message):
            self._analyze_transaction_error(log_entry)
    
    def get_transaction_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of transaction-related errors"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter recent transaction-related logs
        transaction_logs = [
            log for log in self.recent_logs 
            if log.timestamp >= cutoff_time and self._is_transaction_related(log.message)
        ]
        
        if not transaction_logs:
            return {
                'total_errors': 0,
                'error_breakdown': {},
                'hourly_distribution': {},
                'affected_trades': [],
                'common_patterns': []
            }
        
        # Analyze errors
        error_breakdown = defaultdict(int)
        hourly_distribution = defaultdict(int)
        affected_trades = set()
        
        for log in transaction_logs:
            # Error type breakdown
            error_type = log.error_type or self._classify_error(log.message)
            error_breakdown[error_type] += 1
            
            # Hourly distribution
            hour_key = log.timestamp.strftime('%Y-%m-%d %H:00')
            hourly_distribution[hour_key] += 1
            
            # Affected trades
            if log.trade_id:
                affected_trades.add(log.trade_id)
        
        # Find common patterns
        common_patterns = self._find_common_error_patterns(transaction_logs)
        
        return {
            'total_errors': len(transaction_logs),
            'error_breakdown': dict(error_breakdown),
            'hourly_distribution': dict(hourly_distribution),
            'affected_trades': list(affected_trades),
            'common_patterns': common_patterns,
            'time_period_hours': hours
        }
    
    def get_error_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get error trends over time"""
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # Filter logs by time period
        filtered_logs = [
            log for log in self.recent_logs 
            if log.timestamp >= cutoff_time and self._is_transaction_related(log.message)
        ]
        
        # Group by day and error type
        daily_trends = defaultdict(lambda: defaultdict(int))
        
        for log in filtered_logs:
            day_key = log.timestamp.strftime('%Y-%m-%d')
            error_type = log.error_type or self._classify_error(log.message)
            daily_trends[day_key][error_type] += 1
        
        # Convert to list format for easier consumption
        trend_data = []
        for day in sorted(daily_trends.keys()):
            day_data = {'date': day, 'errors': dict(daily_trends[day])}
            day_data['total'] = sum(daily_trends[day].values())
            trend_data.append(day_data)
        
        return {
            'trend_data': trend_data,
            'time_period_days': days,
            'total_errors': len(filtered_logs)
        }
    
    def search_logs(self, 
                   query: str, 
                   hours: int = 24, 
                   trade_id: Optional[int] = None,
                   error_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search logs with filters"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter logs
        filtered_logs = []
        for log in self.recent_logs:
            if log.timestamp < cutoff_time:
                continue
            
            # Text search
            if query and query.lower() not in log.message.lower():
                continue
            
            # Trade ID filter
            if trade_id and log.trade_id != trade_id:
                continue
            
            # Error type filter
            if error_type and log.error_type != error_type:
                continue
            
            filtered_logs.append(log)
        
        # Convert to dict format
        return [
            {
                'timestamp': log.timestamp.isoformat(),
                'level': log.level,
                'message': log.message,
                'logger_name': log.logger_name,
                'trade_id': log.trade_id,
                'error_type': log.error_type,
                'additional_data': log.additional_data
            }
            for log in filtered_logs
        ]
    
    def get_critical_errors(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get critical errors that need immediate attention"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        critical_logs = [
            log for log in self.recent_logs
            if (log.timestamp >= cutoff_time and 
                log.level in ['CRITICAL', 'ERROR'] and
                self._is_transaction_related(log.message))
        ]
        
        # Group by error type for analysis
        critical_by_type = defaultdict(list)
        for log in critical_logs:
            error_type = log.error_type or self._classify_error(log.message)
            critical_by_type[error_type].append(log)
        
        # Format for response
        critical_summary = []
        for error_type, logs in critical_by_type.items():
            critical_summary.append({
                'error_type': error_type,
                'count': len(logs),
                'latest_occurrence': max(log.timestamp for log in logs).isoformat(),
                'affected_trades': list(set(log.trade_id for log in logs if log.trade_id)),
                'sample_messages': [log.message for log in logs[:3]]  # First 3 messages
            })
        
        return sorted(critical_summary, key=lambda x: x['count'], reverse=True)
    
    def export_logs(self, 
                   hours: int = 24, 
                   format: str = 'json',
                   transaction_only: bool = True) -> str:
        """Export logs in specified format"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter logs
        if transaction_only:
            filtered_logs = [
                log for log in self.recent_logs
                if log.timestamp >= cutoff_time and self._is_transaction_related(log.message)
            ]
        else:
            filtered_logs = [
                log for log in self.recent_logs
                if log.timestamp >= cutoff_time
            ]
        
        if format.lower() == 'json':
            return json.dumps([
                {
                    'timestamp': log.timestamp.isoformat(),
                    'level': log.level,
                    'message': log.message,
                    'logger_name': log.logger_name,
                    'trade_id': log.trade_id,
                    'error_type': log.error_type,
                    'additional_data': log.additional_data
                }
                for log in filtered_logs
            ], indent=2)
        
        elif format.lower() == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow(['timestamp', 'level', 'message', 'logger_name', 'trade_id', 'error_type'])
            
            # Data
            for log in filtered_logs:
                writer.writerow([
                    log.timestamp.isoformat(),
                    log.level,
                    log.message,
                    log.logger_name,
                    log.trade_id,
                    log.error_type
                ])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _is_transaction_related(self, message: str) -> bool:
        """Check if log message is transaction-related"""
        
        for pattern in self.compiled_patterns:
            if pattern.search(message):
                return True
        
        # Additional keyword checks
        transaction_keywords = [
            'trade', 'transaction', 'purchase', 'payment', 'blockchain',
            'solana', 'ethereum', 'wallet', 'token', 'usdc'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in transaction_keywords)
    
    def _classify_error(self, message: str) -> str:
        """Classify error type based on message content"""
        
        message_lower = message.lower()
        
        # Check for specific patterns first, then general ones
        if any(word in message_lower for word in ['configuration', 'config', 'missing']):
            return 'configuration_error'
        elif any(word in message_lower for word in ['serialization', 'serialize', 'deserialize']):
            return 'serialization_error'
        elif any(word in message_lower for word in ['validation', 'invalid', 'validate']):
            return 'validation_error'
        elif any(word in message_lower for word in ['blockchain', 'rpc']) and any(word in message_lower for word in ['connection', 'timeout']):
            return 'blockchain_error'
        elif any(word in message_lower for word in ['wallet']) and any(word in message_lower for word in ['connection', 'failed']):
            return 'wallet_error'
        elif any(word in message_lower for word in ['timeout', 'network']):
            return 'network_error'
        elif any(word in message_lower for word in ['wallet', 'address']):
            return 'wallet_error'
        elif any(word in message_lower for word in ['blockchain', 'rpc', 'connection']):
            return 'blockchain_error'
        else:
            return 'unknown_error'
    
    def _analyze_transaction_error(self, log_entry: LogEntry) -> None:
        """Analyze transaction error for patterns"""
        
        error_type = log_entry.error_type or self._classify_error(log_entry.message)
        
        # Update pattern counts
        self.error_patterns[error_type] += 1
        
        # Track trends (hourly)
        hour_key = log_entry.timestamp.strftime('%Y-%m-%d %H')
        self.error_trends[hour_key].append(error_type)
    
    def _find_common_error_patterns(self, logs: List[LogEntry]) -> List[Dict[str, Any]]:
        """Find common error patterns in logs"""
        
        pattern_counts = defaultdict(int)
        
        for log in logs:
            # Extract common patterns from messages
            message = log.message.lower()
            
            # Look for specific error patterns
            if 'buffer' in message and 'end' in message:
                pattern_counts['buffer_end_error'] += 1
            elif 'configuration' in message and 'missing' in message:
                pattern_counts['missing_configuration'] += 1
            elif 'connection' in message and ('failed' in message or 'timeout' in message):
                pattern_counts['connection_failure'] += 1
            elif 'serialization' in message and 'failed' in message:
                pattern_counts['serialization_failure'] += 1
            elif 'invalid' in message and 'address' in message:
                pattern_counts['invalid_address'] += 1
        
        # Convert to list and sort by frequency
        patterns = [
            {'pattern': pattern, 'count': count, 'percentage': (count / len(logs)) * 100}
            for pattern, count in pattern_counts.items()
        ]
        
        return sorted(patterns, key=lambda x: x['count'], reverse=True)


# Global instance
transaction_log_aggregator = TransactionLogAggregator()