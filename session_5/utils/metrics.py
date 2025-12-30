"""
Metrics Collection

Simple in-memory metrics collection for Kafka applications.
Can be extended to Prometheus/StatsD later.
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List


class Metrics:
    """Simple metrics collector"""
    
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()
        self._start_time = time.time()
    
    def increment(self, metric_name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        key = self._build_key(metric_name, labels)
        with self._lock:
            self._counters[key] += value
    
    def gauge(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric"""
        key = self._build_key(metric_name, labels)
        with self._lock:
            self._gauges[key] = value
    
    def histogram(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram value"""
        key = self._build_key(metric_name, labels)
        with self._lock:
            self._histograms[key].append(value)
            # Keep only last 1000 values
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]
    
    def timer(self, metric_name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations"""
        return Timer(self, metric_name, labels)
    
    def _build_key(self, metric_name: str, labels: Dict[str, str] = None) -> str:
        """Build metric key with labels"""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{metric_name}{{{label_str}}}"
        return metric_name
    
    def get_counters(self) -> Dict[str, int]:
        """Get all counter values"""
        with self._lock:
            return dict(self._counters)
    
    def get_gauges(self) -> Dict[str, float]:
        """Get all gauge values"""
        with self._lock:
            return dict(self._gauges)
    
    def get_histogram_stats(self, metric_name: str, labels: Dict[str, str] = None) -> Dict[str, float]:
        """Get histogram statistics"""
        key = self._build_key(metric_name, labels)
        with self._lock:
            values = self._histograms.get(key, [])
            if not values:
                return {}
            
            sorted_values = sorted(values)
            count = len(values)
            return {
                "count": count,
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / count,
                "median": sorted_values[count // 2] if count > 0 else 0,
                "p95": sorted_values[int(count * 0.95)] if count > 0 else 0,
                "p99": sorted_values[int(count * 0.99)] if count > 0 else 0,
            }
    
    def get_all_metrics(self) -> Dict:
        """Get all metrics"""
        return {
            "counters": self.get_counters(),
            "gauges": self.get_gauges(),
            "uptime_seconds": time.time() - self._start_time,
        }


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self, metrics: Metrics, metric_name: str, labels: Dict[str, str] = None):
        self.metrics = metrics
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            elapsed_ms = (time.time() - self.start_time) * 1000
            self.metrics.histogram(self.metric_name, elapsed_ms, self.labels)


# Global metrics instance
_metrics = Metrics()


def get_metrics() -> Metrics:
    """Get global metrics instance"""
    return _metrics


def increment(metric_name: str, value: int = 1, labels: Dict[str, str] = None):
    """Increment a counter"""
    _metrics.increment(metric_name, value, labels)


def gauge(metric_name: str, value: float, labels: Dict[str, str] = None):
    """Set a gauge"""
    _metrics.gauge(metric_name, value, labels)


def histogram(metric_name: str, value: float, labels: Dict[str, str] = None):
    """Record a histogram value"""
    _metrics.histogram(metric_name, value, labels)


def timer(metric_name: str, labels: Dict[str, str] = None):
    """Get a timer context manager"""
    return _metrics.timer(metric_name, labels)

