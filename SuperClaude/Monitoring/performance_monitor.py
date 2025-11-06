"""
Performance Monitoring System for SuperClaude.

Tracks metrics, performance, and resource usage across all components.
"""

import time
import psutil
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics to track."""

    COUNTER = "counter"      # Incremental count
    GAUGE = "gauge"          # Current value
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"          # Execution time
    RATE = "rate"           # Events per second


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Individual metric data point."""

    name: str
    type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Performance alert."""

    id: str
    severity: AlertSeverity
    metric_name: str
    message: str
    threshold: float
    current_value: float
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False


@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    active_tasks: int
    thread_count: int
    process_count: int


from .sink import JsonlMetricsSink, MetricsSink
from .sqlite_sink import SQLiteMetricsSink


class PerformanceMonitor:
    """
    Monitors SuperClaude performance and resource usage.

    Features:
    - Real-time metrics collection
    - Performance alerting
    - Resource tracking
    - Bottleneck detection
    - Historical analysis
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, sinks: Optional[list] = None):
        """Initialize performance monitor."""
        self.config = config or {}
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.snapshots: deque = deque(maxlen=1000)
        self.start_time = datetime.now()
        self.is_monitoring = False
        self.monitor_task = None
        self.token_usage_counters = defaultdict(lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0})
        self.token_usage_history = deque(maxlen=10000)

        # Persistence sinks (best-effort)
        self.sinks: List[MetricsSink] = []
        if sinks:
            self.sinks.extend(sinks)
        elif self.config.get('persist_metrics', True):
            # Default to SQLite sink with JSONL as secondary
            self.sinks.append(SQLiteMetricsSink())
            self.sinks.append(JsonlMetricsSink())

        # Performance thresholds
        self.thresholds = {
            'cpu_percent': self.config.get('cpu_threshold', 80),
            'memory_percent': self.config.get('memory_threshold', 85),
            'response_time_ms': self.config.get('response_time_threshold', 1000),
            'error_rate': self.config.get('error_rate_threshold', 0.05)
        }

        # Metric aggregators
        self.aggregators = {
            MetricType.COUNTER: self._aggregate_counter,
            MetricType.GAUGE: self._aggregate_gauge,
            MetricType.HISTOGRAM: self._aggregate_histogram,
            MetricType.TIMER: self._aggregate_timer,
            MetricType.RATE: self._aggregate_rate
        }

    async def start_monitoring(self, interval_seconds: int = 10):
        """
        Start continuous monitoring.

        Args:
            interval_seconds: Monitoring interval
        """
        if self.is_monitoring:
            logger.warning("Monitoring already started")
            return

        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info(f"Started performance monitoring (interval: {interval_seconds}s)")

    async def stop_monitoring(self):
        """Stop continuous monitoring."""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                logger.debug("Monitoring task cancelled", exc_info=True)

        logger.info("Stopped performance monitoring")

    # Compatibility helpers expected by some tests
    def start_collection(self):
        """One-shot metric collection for synchronous environments."""
        try:
            self.take_snapshot()
        except Exception:
            logger.debug("Snapshot collection failed", exc_info=True)

    def get_metrics(self) -> Dict[str, Any]:
        """Return a simplified metrics snapshot for quick checks."""
        snap = self.snapshots[-1] if self.snapshots else None
        tokens_snapshot = self.token_usage_counters.get("aggregate", {})
        return {
            'cpu_percent': getattr(snap, 'cpu_percent', 0.0),
            'memory_percent': getattr(snap, 'memory_percent', 0.0),
            'token_prompt_total': tokens_snapshot.get('prompt_tokens', 0),
            'token_completion_total': tokens_snapshot.get('completion_tokens', 0),
            'token_total': tokens_snapshot.get('total_tokens', 0),
            'token_calls': tokens_snapshot.get('calls', 0)
        }

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Record a metric.

        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            tags: Optional tags
        """
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            tags=tags or {}
        )

        self.metrics[name].append(metric)

        # Check alert rules
        self._check_alerts(metric)

        logger.debug(f"Recorded metric: {name}={value}")

        # Persist event (best-effort)
        event = {
            'type': 'metric',
            'data': {
                'name': metric.name,
                'type': metric.type.value,
                'value': metric.value,
                'timestamp': metric.timestamp.isoformat(),
                'tags': metric.tags,
            }
        }
        for sink in self.sinks:
            try:
                sink.write_event(event)
            except Exception:
                logger.debug("Failed to persist metric event via %s", sink, exc_info=True)

    def record_token_usage(
        self,
        *,
        model: Optional[str],
        provider: Optional[str],
        usage: Dict[str, int],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record token usage statistics for model invocations.

        Args:
            model: Model identifier (optional).
            provider: Provider name (optional).
            usage: Dict containing token counts (prompt_tokens, completion_tokens, total_tokens).
            metadata: Additional context (optional).
        """
        model_key = model or "unknown"
        provider_key = provider or "unknown"
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))

        timestamp = datetime.now()

        entry = {
            "timestamp": timestamp.isoformat(),
            "model": model_key,
            "provider": provider_key,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "metadata": metadata or {},
        }
        self.token_usage_history.append(entry)

        for key in {"aggregate", provider_key, model_key, f"{provider_key}:{model_key}"}:
            bucket = self.token_usage_counters[key]
            bucket["prompt_tokens"] += prompt_tokens
            bucket["completion_tokens"] += completion_tokens
            bucket["total_tokens"] += total_tokens
            bucket["calls"] += 1

        self.record_metric(
            "token.usage.total",
            float(total_tokens),
            MetricType.COUNTER,
            tags={"provider": provider_key, "model": model_key},
        )
        self.record_metric(
            "token.usage.prompt",
            float(prompt_tokens),
            MetricType.COUNTER,
            tags={"provider": provider_key, "model": model_key},
        )
        self.record_metric(
            "token.usage.completion",
            float(completion_tokens),
            MetricType.COUNTER,
            tags={"provider": provider_key, "model": model_key},
        )

        token_event = {
            "type": "token_usage",
            "data": {
                **entry,
                "counters": [
                    {
                        "key": "aggregate",
                        **self.token_usage_counters["aggregate"],
                    },
                    {
                        "key": provider_key,
                        **self.token_usage_counters[provider_key],
                    },
                    {
                        "key": model_key,
                        **self.token_usage_counters[model_key],
                    },
                    {
                        "key": f"{provider_key}:{model_key}",
                        **self.token_usage_counters[f"{provider_key}:{model_key}"],
                    },
                ],
            },
        }
        for sink in self.sinks:
            try:
                sink.write_event(token_event)
            except Exception:
                logger.debug("Failed to persist token usage event via %s", sink, exc_info=True)

    def record_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Persist a structured monitoring event."""
        payload = {
            'type': event_type,
            'data': dict(data),
        }
        for sink in self.sinks:
            try:
                sink.write_event(payload)
            except Exception:
                logger.debug("Failed to persist custom event via %s", sink, exc_info=True)

    def start_timer(self, name: str) -> Callable:
        """
        Start a timer for measuring execution time.

        Args:
            name: Timer name

        Returns:
            Stop function to call when done
        """
        start_time = time.perf_counter()

        def stop():
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.record_metric(name, duration_ms, MetricType.TIMER)
            return duration_ms

        return stop

    async def measure_async(self, name: str, coroutine):
        """
        Measure execution time of async operation.

        Args:
            name: Metric name
            coroutine: Coroutine to measure

        Returns:
            Coroutine result
        """
        start_time = time.perf_counter()

        try:
            result = await coroutine
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.record_metric(f"{name}.duration", duration_ms, MetricType.TIMER)
            self.record_metric(f"{name}.success", 1, MetricType.COUNTER)
            return result

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.record_metric(f"{name}.duration", duration_ms, MetricType.TIMER)
            self.record_metric(f"{name}.error", 1, MetricType.COUNTER)
            raise

    def take_snapshot(self) -> PerformanceSnapshot:
        """
        Take a performance snapshot.

        Returns:
            Current performance snapshot
        """
        process = psutil.Process()
        cpu_percent = process.cpu_percent()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()

        # Get IO counters
        try:
            io_counters = process.io_counters()
            disk_read_mb = io_counters.read_bytes / 1024 / 1024
            disk_write_mb = io_counters.write_bytes / 1024 / 1024
        except:
            disk_read_mb = 0
            disk_write_mb = 0

        # Get network stats
        try:
            net_io = psutil.net_io_counters()
            net_sent_mb = net_io.bytes_sent / 1024 / 1024
            net_recv_mb = net_io.bytes_recv / 1024 / 1024
        except:
            net_sent_mb = 0
            net_recv_mb = 0

        snapshot = PerformanceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_mb=memory_info.rss / 1024 / 1024,
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_sent_mb=net_sent_mb,
            network_recv_mb=net_recv_mb,
            active_tasks=len(asyncio.all_tasks()),
            thread_count=process.num_threads(),
            process_count=1
        )

        self.snapshots.append(snapshot)

        # Record as metrics
        self.record_metric("system.cpu_percent", cpu_percent, MetricType.GAUGE)
        self.record_metric("system.memory_percent", memory_percent, MetricType.GAUGE)
        self.record_metric("system.memory_mb", snapshot.memory_mb, MetricType.GAUGE)

        # Persist snapshot (best-effort)
        event = {
            'type': 'snapshot',
            'data': {
                'timestamp': snapshot.timestamp.isoformat(),
                'cpu_percent': snapshot.cpu_percent,
                'memory_percent': snapshot.memory_percent,
                'memory_mb': snapshot.memory_mb,
                'disk_io_read_mb': snapshot.disk_io_read_mb,
                'disk_io_write_mb': snapshot.disk_io_write_mb,
                'network_sent_mb': snapshot.network_sent_mb,
                'network_recv_mb': snapshot.network_recv_mb,
                'active_tasks': snapshot.active_tasks,
                'thread_count': snapshot.thread_count,
                'process_count': snapshot.process_count,
            }
        }
        for sink in self.sinks:
            try:
                sink.write_event(event)
            except Exception:
                logger.debug("Failed to persist alert via %s", sink, exc_info=True)

        return snapshot

    def add_alert_rule(
        self,
        metric_name: str,
        threshold: float,
        condition: str = "greater",
        severity: AlertSeverity = AlertSeverity.WARNING
    ):
        """
        Add an alert rule.

        Args:
            metric_name: Metric to monitor
            threshold: Alert threshold
            condition: Condition (greater, less, equal)
            severity: Alert severity
        """
        rule = {
            'metric_name': metric_name,
            'threshold': threshold,
            'condition': condition,
            'severity': severity
        }

        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {metric_name} {condition} {threshold}")

    def get_metrics_summary(self, metric_name: str = None) -> Dict[str, Any]:
        """
        Get metrics summary.

        Args:
            metric_name: Optional specific metric

        Returns:
            Metrics summary
        """
        if metric_name:
            metrics = list(self.metrics.get(metric_name, []))
            if not metrics:
                return {}

            metric_type = metrics[0].type if metrics else MetricType.GAUGE
            return self.aggregators[metric_type](metrics)

        # Get all metrics summary
        summary = {}
        for name, metric_list in self.metrics.items():
            if metric_list:
                metric_type = metric_list[0].type
                summary[name] = self.aggregators[metric_type](list(metric_list))

        return summary

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report.

        Returns:
            Performance report
        """
        uptime = (datetime.now() - self.start_time).total_seconds()

        # Get latest snapshot
        latest_snapshot = self.snapshots[-1] if self.snapshots else None

        # Calculate aggregates
        metrics_summary = self.get_metrics_summary()

        # Get active alerts
        active_alerts = [
            {
                'id': alert.id,
                'severity': alert.severity.value,
                'message': alert.message,
                'metric': alert.metric_name,
                'value': alert.current_value,
                'threshold': alert.threshold
            }
            for alert in self.alerts.values()
            if not alert.resolved
        ]

        report = {
            'uptime_seconds': uptime,
            'start_time': self.start_time.isoformat(),
            'current_snapshot': self._serialize_snapshot(latest_snapshot),
            'metrics_summary': metrics_summary,
            'active_alerts': active_alerts,
            'alert_count': len(active_alerts),
            'total_metrics_recorded': sum(len(m) for m in self.metrics.values())
        }

        return report

    def detect_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Detect performance bottlenecks.

        Returns:
            List of detected bottlenecks
        """
        bottlenecks = []

        # Check CPU bottleneck
        cpu_metrics = list(self.metrics.get("system.cpu_percent", []))
        if cpu_metrics:
            recent_cpu = [m.value for m in cpu_metrics[-10:]]
            avg_cpu = sum(recent_cpu) / len(recent_cpu)

            if avg_cpu > self.thresholds['cpu_percent']:
                bottlenecks.append({
                    'type': 'CPU',
                    'severity': 'high' if avg_cpu > 90 else 'medium',
                    'value': avg_cpu,
                    'threshold': self.thresholds['cpu_percent'],
                    'suggestion': 'Consider optimizing CPU-intensive operations or scaling horizontally'
                })

        # Check memory bottleneck
        mem_metrics = list(self.metrics.get("system.memory_percent", []))
        if mem_metrics:
            recent_mem = [m.value for m in mem_metrics[-10:]]
            avg_mem = sum(recent_mem) / len(recent_mem)

            if avg_mem > self.thresholds['memory_percent']:
                bottlenecks.append({
                    'type': 'Memory',
                    'severity': 'high' if avg_mem > 95 else 'medium',
                    'value': avg_mem,
                    'threshold': self.thresholds['memory_percent'],
                    'suggestion': 'Consider optimizing memory usage or increasing available memory'
                })

        # Check response time bottleneck
        timer_metrics = {
            name: list(metrics)
            for name, metrics in self.metrics.items()
            if metrics and metrics[0].type == MetricType.TIMER
        }

        for name, metrics in timer_metrics.items():
            recent_times = [m.value for m in metrics[-10:]]
            if recent_times:
                avg_time = sum(recent_times) / len(recent_times)

                if avg_time > self.thresholds['response_time_ms']:
                    bottlenecks.append({
                        'type': 'Response Time',
                        'metric': name,
                        'severity': 'high' if avg_time > 2000 else 'medium',
                        'value': avg_time,
                        'threshold': self.thresholds['response_time_ms'],
                        'suggestion': f'Optimize {name} operation for better performance'
                    })

        return bottlenecks

    def export_metrics(self, filepath: str):
        """
        Export metrics to file.

        Args:
            filepath: Export file path
        """
        data = {
            'report': self.get_performance_report(),
            'bottlenecks': self.detect_bottlenecks(),
            'metrics': {
                name: [self._serialize_metric(m) for m in list(metrics)]
                for name, metrics in self.metrics.items()
            },
            'snapshots': [self._serialize_snapshot(s) for s in self.snapshots]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Exported metrics to: {filepath}")

    # Private helper methods

    async def _monitoring_loop(self, interval: int):
        """Continuous monitoring loop."""
        while self.is_monitoring:
            try:
                # Take snapshot
                self.take_snapshot()

                # Check for bottlenecks
                bottlenecks = self.detect_bottlenecks()
                if bottlenecks:
                    for bottleneck in bottlenecks:
                        logger.warning(f"Bottleneck detected: {bottleneck}")

                # Wait for next interval
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)

    def _check_alerts(self, metric: Metric):
        """Check if metric triggers any alerts."""
        for rule in self.alert_rules:
            if metric.name != rule['metric_name']:
                continue

            triggered = False
            if rule['condition'] == 'greater' and metric.value > rule['threshold']:
                triggered = True
            elif rule['condition'] == 'less' and metric.value < rule['threshold']:
                triggered = True
            elif rule['condition'] == 'equal' and metric.value == rule['threshold']:
                triggered = True

            if triggered:
                alert_id = f"{metric.name}_{rule['condition']}_{rule['threshold']}"

                if alert_id not in self.alerts or self.alerts[alert_id].resolved:
                    alert = Alert(
                        id=alert_id,
                        severity=rule['severity'],
                        metric_name=metric.name,
                        message=f"{metric.name} {rule['condition']} {rule['threshold']}",
                        threshold=rule['threshold'],
                        current_value=metric.value
                    )

                    self.alerts[alert_id] = alert
                    logger.warning(f"Alert triggered: {alert.message} (current: {metric.value})")
                    # Persist alert
                    event = {
                        'type': 'alert',
                        'data': {
                            'id': alert.id,
                            'severity': alert.severity.value,
                            'metric_name': alert.metric_name,
                            'message': alert.message,
                            'threshold': alert.threshold,
                            'current_value': alert.current_value,
                            'timestamp': alert.timestamp.isoformat(),
                        }
                    }
                    for sink in self.sinks:
                        try:
                            sink.write_event(event)
                        except Exception:
                            logger.debug("Failed to persist snapshot via %s", sink, exc_info=True)

            else:
                # Resolve alert if it exists
                alert_id = f"{metric.name}_{rule['condition']}_{rule['threshold']}"
                if alert_id in self.alerts and not self.alerts[alert_id].resolved:
                    self.alerts[alert_id].resolved = True
                    logger.info(f"Alert resolved: {self.alerts[alert_id].message}")

    def _aggregate_counter(self, metrics: List[Metric]) -> Dict[str, float]:
        """Aggregate counter metrics."""
        if not metrics:
            return {}

        total = sum(m.value for m in metrics)
        return {
            'total': total,
            'count': len(metrics),
            'rate_per_second': total / max(1, (metrics[-1].timestamp - metrics[0].timestamp).total_seconds())
        }

    def _aggregate_gauge(self, metrics: List[Metric]) -> Dict[str, float]:
        """Aggregate gauge metrics."""
        if not metrics:
            return {}

        values = [m.value for m in metrics]
        return {
            'current': values[-1],
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values)
        }

    def _aggregate_histogram(self, metrics: List[Metric]) -> Dict[str, float]:
        """Aggregate histogram metrics."""
        if not metrics:
            return {}

        values = sorted([m.value for m in metrics])
        count = len(values)

        return {
            'count': count,
            'min': values[0],
            'max': values[-1],
            'avg': sum(values) / count,
            'p50': values[count // 2],
            'p95': values[int(count * 0.95)],
            'p99': values[int(count * 0.99)]
        }

    def _aggregate_timer(self, metrics: List[Metric]) -> Dict[str, float]:
        """Aggregate timer metrics."""
        return self._aggregate_histogram(metrics)

    def _aggregate_rate(self, metrics: List[Metric]) -> Dict[str, float]:
        """Aggregate rate metrics."""
        if not metrics:
            return {}

        time_window = (metrics[-1].timestamp - metrics[0].timestamp).total_seconds()
        if time_window == 0:
            return {'rate_per_second': 0}

        total = sum(m.value for m in metrics)
        return {
            'rate_per_second': total / time_window,
            'total_events': total
        }

    def _serialize_metric(self, metric: Metric) -> Dict[str, Any]:
        """Serialize metric for export."""
        return {
            'name': metric.name,
            'type': metric.type.value,
            'value': metric.value,
            'timestamp': metric.timestamp.isoformat(),
            'tags': metric.tags
        }

    def _serialize_snapshot(self, snapshot: Optional[PerformanceSnapshot]) -> Optional[Dict[str, Any]]:
        """Serialize snapshot for export."""
        if not snapshot:
            return None

        return {
            'timestamp': snapshot.timestamp.isoformat(),
            'cpu_percent': snapshot.cpu_percent,
            'memory_percent': snapshot.memory_percent,
            'memory_mb': snapshot.memory_mb,
            'disk_io_read_mb': snapshot.disk_io_read_mb,
            'disk_io_write_mb': snapshot.disk_io_write_mb,
            'network_sent_mb': snapshot.network_sent_mb,
            'network_recv_mb': snapshot.network_recv_mb,
            'active_tasks': snapshot.active_tasks,
            'thread_count': snapshot.thread_count
        }


# Global monitor instance
_global_monitor = None


def get_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


# Convenience decorators

def measure_performance(metric_name: str = None):
    """Decorator to measure function performance."""
    def decorator(func):
        name = metric_name or f"{func.__module__}.{func.__name__}"

        async def async_wrapper(*args, **kwargs):
            monitor = get_monitor()
            return await monitor.measure_async(name, func(*args, **kwargs))

        def sync_wrapper(*args, **kwargs):
            monitor = get_monitor()
            stop_timer = monitor.start_timer(name)
            try:
                result = func(*args, **kwargs)
                stop_timer()
                monitor.record_metric(f"{name}.success", 1, MetricType.COUNTER)
                return result
            except Exception as e:
                stop_timer()
                monitor.record_metric(f"{name}.error", 1, MetricType.COUNTER)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
