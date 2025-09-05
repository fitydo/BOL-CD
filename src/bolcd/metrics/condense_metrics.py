"""
Prometheus Metrics for Condensed Alert System
"""
from prometheus_client import Counter, Gauge, Histogram, Summary
import time
from functools import wraps

# Counters
alerts_total = Counter(
    "bolcd_alerts_total",
    "Total number of alerts processed",
    ["severity", "entity_id"]
)

decisions_total = Counter(
    "bolcd_decisions_total",
    "Total number of decisions made",
    ["decision", "reason"]
)

suppress_total = Counter(
    "bolcd_suppress_total",
    "Total suppressed alerts",
    ["severity", "edge_id"]
)

deliver_total = Counter(
    "bolcd_deliver_total",
    "Total delivered alerts",
    ["severity", "reason"]
)

late_replay_total = Counter(
    "bolcd_late_replay_total",
    "Total late replay alerts",
    ["reason"]
)

false_suppression_total = Counter(
    "bolcd_false_suppression_total",
    "Total false suppressions detected",
    ["method"]
)

# Gauges
suppression_rate = Gauge(
    "bolcd_suppression_rate",
    "Current suppression rate"
)

false_suppression_rate = Gauge(
    "bolcd_false_suppression_rate",
    "Current false suppression rate"
)

pending_late_replay = Gauge(
    "bolcd_pending_late_replay",
    "Number of pending late replay alerts"
)

active_api_keys = Gauge(
    "bolcd_active_api_keys",
    "Number of active API keys",
    ["scope"]
)

# Histograms
decision_latency = Histogram(
    "bolcd_decision_latency_seconds",
    "Decision latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

validation_score_distribution = Histogram(
    "bolcd_validation_score",
    "False suppression validation score distribution",
    ["method"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

api_request_duration = Histogram(
    "bolcd_api_request_duration_seconds",
    "API request duration",
    ["endpoint", "method", "status"]
)

# Summary
late_replay_delay = Summary(
    "bolcd_late_replay_delay_seconds",
    "Delay between suppression and late replay"
)

# Decorator for timing functions
def observe_duration(metric):
    """Decorator to observe function duration"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                metric.observe(duration)
        return wrapper
    return decorator

# Helper functions
def record_alert(alert):
    """Record alert metrics"""
    alerts_total.labels(
        severity=alert.severity,
        entity_id=alert.entity_id
    ).inc()

def record_decision(decision_type: str, reason: str, alert=None):
    """Record decision metrics"""
    decisions_total.labels(
        decision=decision_type,
        reason=reason
    ).inc()
    
    if decision_type == "suppress" and alert:
        suppress_total.labels(
            severity=alert.severity,
            edge_id=reason.get("edge_id", "unknown")
        ).inc()
    elif decision_type == "deliver" and alert:
        deliver_total.labels(
            severity=alert.severity,
            reason=reason.get("why", "unknown")
        ).inc()

def record_late_replay(reason: str):
    """Record late replay metrics"""
    late_replay_total.labels(reason=reason).inc()

def record_false_suppression(method: str, score: float):
    """Record false suppression detection"""
    validation_score_distribution.labels(method=method).observe(score)
    if score > 0.5:  # Threshold for counting as false suppression
        false_suppression_total.labels(method=method).inc()

def update_rates(delivered: int, suppressed: int, false_suppressions: int):
    """Update rate gauges"""
    total = delivered + suppressed
    if total > 0:
        suppression_rate.set(suppressed / total)
        if suppressed > 0:
            false_suppression_rate.set(false_suppressions / suppressed)
        else:
            false_suppression_rate.set(0)
    else:
        suppression_rate.set(0)
        false_suppression_rate.set(0)
