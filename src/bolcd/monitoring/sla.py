"""SLA (Service Level Agreement) Monitoring for BOL-CD

Tracks and reports on SLA compliance including uptime, performance,
and response time metrics.
"""

from __future__ import annotations

import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
import statistics

import prometheus_client
from prometheus_client import Counter, Gauge, Histogram, Summary


# Prometheus metrics for SLA monitoring
sla_uptime_gauge = Gauge('bolcd_sla_uptime_percentage', 'Current uptime percentage')
sla_availability_gauge = Gauge('bolcd_sla_availability_percentage', 'Service availability percentage')
sla_response_time_histogram = Histogram('bolcd_sla_response_time_seconds', 'Response time distribution', buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0])
sla_error_rate_gauge = Gauge('bolcd_sla_error_rate', 'Error rate percentage')
sla_throughput_gauge = Gauge('bolcd_sla_throughput_eps', 'Current throughput in events per second')
sla_violations_counter = Counter('bolcd_sla_violations_total', 'Total SLA violations', ['type'])


@dataclass
class SLATarget:
    """SLA target definition"""
    name: str
    target_value: float
    unit: str
    measurement_window: int  # seconds
    critical: bool = False
    
    def is_met(self, current_value: float) -> bool:
        """Check if SLA target is met"""
        if "uptime" in self.name or "availability" in self.name:
            return current_value >= self.target_value
        elif "response" in self.name or "latency" in self.name:
            return current_value <= self.target_value
        elif "error" in self.name:
            return current_value <= self.target_value
        elif "throughput" in self.name:
            return current_value >= self.target_value
        return True


@dataclass
class SLAMetrics:
    """Current SLA metrics"""
    timestamp: str
    uptime_percentage: float
    availability_percentage: float
    response_time_p50: float
    response_time_p95: float
    response_time_p99: float
    error_rate: float
    throughput_eps: float
    violations: List[str]
    status: str  # "healthy", "degraded", "critical"


class SLAMonitor:
    """Monitors and tracks SLA compliance"""
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        data_path: Optional[str] = None
    ):
        self.config_file = Path(config_file or "./configs/sla.yaml")
        self.data_path = Path(data_path or "./data/sla")
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Default SLA targets
        self.targets = self._load_default_targets()
        
        # Load custom targets from config
        self._load_config()
        
        # Metrics storage (in-memory circular buffer)
        self.uptime_events = deque(maxlen=10000)  # Last 10k events
        self.response_times = deque(maxlen=10000)
        self.error_events = deque(maxlen=10000)
        self.throughput_samples = deque(maxlen=1000)
        
        # State tracking
        self.service_start_time = time.time()
        self.last_health_check = time.time()
        self.total_requests = 0
        self.failed_requests = 0
        self.downtime_periods: List[Tuple[float, float]] = []
        self.current_downtime_start: Optional[float] = None
    
    def _load_default_targets(self) -> Dict[str, SLATarget]:
        """Load default SLA targets based on plan tier"""
        import os
        plan_tier = os.getenv("BOLCD_PLAN_TIER", "standard").lower()
        
        if plan_tier == "enterprise":
            return {
                "uptime": SLATarget("uptime", 99.9, "%", 86400, critical=True),  # 99.9% daily
                "availability": SLATarget("availability", 99.95, "%", 2592000, critical=True),  # 99.95% monthly
                "response_p95": SLATarget("response_p95", 0.1, "seconds", 3600),  # 100ms p95
                "response_p99": SLATarget("response_p99", 0.5, "seconds", 3600),  # 500ms p99
                "error_rate": SLATarget("error_rate", 0.1, "%", 3600),  # 0.1% error rate
                "throughput": SLATarget("throughput", 50000, "eps", 60)  # 50k events/sec
            }
        elif plan_tier == "standard":
            return {
                "uptime": SLATarget("uptime", 99.5, "%", 86400, critical=True),  # 99.5% daily
                "availability": SLATarget("availability", 99.9, "%", 2592000, critical=True),  # 99.9% monthly
                "response_p95": SLATarget("response_p95", 0.2, "seconds", 3600),  # 200ms p95
                "response_p99": SLATarget("response_p99", 1.0, "seconds", 3600),  # 1s p99
                "error_rate": SLATarget("error_rate", 0.5, "%", 3600),  # 0.5% error rate
                "throughput": SLATarget("throughput", 10000, "eps", 60)  # 10k events/sec
            }
        else:  # starter
            return {
                "uptime": SLATarget("uptime", 99.0, "%", 86400),  # 99% daily
                "availability": SLATarget("availability", 99.5, "%", 2592000),  # 99.5% monthly
                "response_p95": SLATarget("response_p95", 0.5, "seconds", 3600),  # 500ms p95
                "response_p99": SLATarget("response_p99", 2.0, "seconds", 3600),  # 2s p99
                "error_rate": SLATarget("error_rate", 1.0, "%", 3600),  # 1% error rate
                "throughput": SLATarget("throughput", 1000, "eps", 60)  # 1k events/sec
            }
    
    def _load_config(self):
        """Load custom SLA targets from config"""
        if not self.config_file.exists():
            return
        
        try:
            import yaml
            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f)
            
            for name, target_config in config.get("sla_targets", {}).items():
                self.targets[name] = SLATarget(
                    name=name,
                    target_value=target_config["value"],
                    unit=target_config.get("unit", "%"),
                    measurement_window=target_config.get("window_seconds", 3600),
                    critical=target_config.get("critical", False)
                )
        except Exception as e:
            print(f"Failed to load SLA config: {e}")
    
    def record_request(
        self,
        response_time: float,
        success: bool = True,
        timestamp: Optional[float] = None
    ):
        """Record a request for SLA tracking"""
        timestamp = timestamp or time.time()
        
        self.total_requests += 1
        self.response_times.append((timestamp, response_time))
        
        if not success:
            self.failed_requests += 1
            self.error_events.append(timestamp)
        
        # Update Prometheus metrics
        sla_response_time_histogram.observe(response_time)
        
        # Check for downtime
        if not success and self.current_downtime_start is None:
            self.current_downtime_start = timestamp
        elif success and self.current_downtime_start is not None:
            self.downtime_periods.append((self.current_downtime_start, timestamp))
            self.current_downtime_start = None
    
    def record_throughput(self, events_processed: int, duration: float):
        """Record throughput sample"""
        timestamp = time.time()
        eps = events_processed / duration if duration > 0 else 0
        self.throughput_samples.append((timestamp, eps))
        sla_throughput_gauge.set(eps)
    
    def calculate_metrics(self) -> SLAMetrics:
        """Calculate current SLA metrics"""
        current_time = time.time()
        
        # Calculate uptime
        total_uptime = current_time - self.service_start_time
        total_downtime = sum(end - start for start, end in self.downtime_periods)
        if self.current_downtime_start:
            total_downtime += current_time - self.current_downtime_start
        
        uptime_percentage = ((total_uptime - total_downtime) / total_uptime * 100) if total_uptime > 0 else 100
        
        # Calculate availability (requests-based)
        availability_percentage = ((self.total_requests - self.failed_requests) / self.total_requests * 100) if self.total_requests > 0 else 100
        
        # Calculate response time percentiles
        recent_response_times = [rt for ts, rt in self.response_times if current_time - ts < 3600]  # Last hour
        if recent_response_times:
            response_times_sorted = sorted(recent_response_times)
            p50 = response_times_sorted[len(response_times_sorted) // 2]
            p95 = response_times_sorted[int(len(response_times_sorted) * 0.95)]
            p99 = response_times_sorted[int(len(response_times_sorted) * 0.99)]
        else:
            p50 = p95 = p99 = 0
        
        # Calculate error rate
        recent_errors = sum(1 for ts in self.error_events if current_time - ts < 3600)
        recent_total = sum(1 for ts, _ in self.response_times if current_time - ts < 3600)
        error_rate = (recent_errors / recent_total * 100) if recent_total > 0 else 0
        
        # Calculate average throughput
        recent_throughput = [eps for ts, eps in self.throughput_samples if current_time - ts < 60]  # Last minute
        avg_throughput = statistics.mean(recent_throughput) if recent_throughput else 0
        
        # Check for violations
        violations = []
        if uptime_percentage < self.targets["uptime"].target_value:
            violations.append(f"Uptime below {self.targets['uptime'].target_value}%")
            sla_violations_counter.labels(type="uptime").inc()
        
        if availability_percentage < self.targets["availability"].target_value:
            violations.append(f"Availability below {self.targets['availability'].target_value}%")
            sla_violations_counter.labels(type="availability").inc()
        
        if p95 > self.targets["response_p95"].target_value:
            violations.append(f"P95 response time above {self.targets['response_p95'].target_value}s")
            sla_violations_counter.labels(type="response_p95").inc()
        
        if p99 > self.targets["response_p99"].target_value:
            violations.append(f"P99 response time above {self.targets['response_p99'].target_value}s")
            sla_violations_counter.labels(type="response_p99").inc()
        
        if error_rate > self.targets["error_rate"].target_value:
            violations.append(f"Error rate above {self.targets['error_rate'].target_value}%")
            sla_violations_counter.labels(type="error_rate").inc()
        
        if avg_throughput < self.targets["throughput"].target_value:
            violations.append(f"Throughput below {self.targets['throughput'].target_value} eps")
            sla_violations_counter.labels(type="throughput").inc()
        
        # Determine overall status
        # A critical violation exists if any critical target is not met
        critical_violations = any(
            True for name, target in self.targets.items()
            if target.critical and not target.is_met(locals().get(name, 0))
        )
        
        if critical_violations:
            status = "critical"
        elif violations:
            status = "degraded"
        else:
            status = "healthy"
        
        # Update Prometheus metrics
        sla_uptime_gauge.set(uptime_percentage)
        sla_availability_gauge.set(availability_percentage)
        sla_error_rate_gauge.set(error_rate)
        
        return SLAMetrics(
            timestamp=datetime.utcnow().isoformat(),
            uptime_percentage=uptime_percentage,
            availability_percentage=availability_percentage,
            response_time_p50=p50,
            response_time_p95=p95,
            response_time_p99=p99,
            error_rate=error_rate,
            throughput_eps=avg_throughput,
            violations=violations,
            status=status
        )
    
    def get_sla_report(self, period_days: int = 30) -> Dict[str, Any]:
        """Generate SLA compliance report"""
        current_metrics = self.calculate_metrics()
        
        # Load historical data
        historical_data = self._load_historical_data(period_days)
        
        # Calculate compliance percentages
        compliance = {}
        for name, target in self.targets.items():
            if name == "uptime":
                compliance[name] = (current_metrics.uptime_percentage >= target.target_value)
            elif name == "availability":
                compliance[name] = (current_metrics.availability_percentage >= target.target_value)
            elif name == "response_p95":
                compliance[name] = (current_metrics.response_time_p95 <= target.target_value)
            elif name == "response_p99":
                compliance[name] = (current_metrics.response_time_p99 <= target.target_value)
            elif name == "error_rate":
                compliance[name] = (current_metrics.error_rate <= target.target_value)
            elif name == "throughput":
                compliance[name] = (current_metrics.throughput_eps >= target.target_value)
        
        # Calculate credits (for SLA violations)
        credits = self._calculate_sla_credits(current_metrics, period_days)
        
        report = {
            "period": {
                "days": period_days,
                "start": (datetime.utcnow() - timedelta(days=period_days)).isoformat(),
                "end": datetime.utcnow().isoformat()
            },
            "current_metrics": asdict(current_metrics),
            "targets": {name: asdict(target) for name, target in self.targets.items()},
            "compliance": compliance,
            "overall_compliance": all(compliance.values()),
            "credits": credits,
            "historical_summary": self._calculate_historical_summary(historical_data),
            "incidents": self._get_recent_incidents()
        }
        
        # Save report
        self._save_report(report)
        
        return report
    
    def _load_historical_data(self, period_days: int) -> List[Dict]:
        """Load historical SLA data"""
        historical = []
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Load from stored metrics files
        metrics_path = self.data_path / "metrics"
        if metrics_path.exists():
            for file_path in sorted(metrics_path.glob("*.json")):
                try:
                    file_date = datetime.strptime(file_path.stem, "%Y%m%d")
                    if file_date >= cutoff_date:
                        with open(file_path, "r") as f:
                            historical.append(json.load(f))
                except:
                    continue
        
        return historical
    
    def _calculate_sla_credits(self, metrics: SLAMetrics, period_days: int) -> Dict[str, Any]:
        """Calculate SLA credits for violations"""
        credits = {
            "percentage": 0,
            "details": []
        }
        
        # Simple credit calculation based on violations
        if metrics.uptime_percentage < self.targets["uptime"].target_value:
            violation_amount = self.targets["uptime"].target_value - metrics.uptime_percentage
            credit_percent = min(violation_amount * 10, 100)  # 10% credit per 1% violation, max 100%
            credits["percentage"] = credit_percent
            credits["details"].append(f"Uptime violation: {credit_percent}% credit")
        
        if metrics.availability_percentage < self.targets["availability"].target_value:
            violation_amount = self.targets["availability"].target_value - metrics.availability_percentage
            credit_percent = min(violation_amount * 5, 50)  # 5% credit per 1% violation, max 50%
            credits["percentage"] = max(credits["percentage"], credit_percent)
            credits["details"].append(f"Availability violation: {credit_percent}% credit")
        
        return credits
    
    def _calculate_historical_summary(self, historical_data: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics from historical data"""
        if not historical_data:
            return {}
        
        summary = {
            "avg_uptime": statistics.mean(d.get("uptime_percentage", 100) for d in historical_data),
            "avg_availability": statistics.mean(d.get("availability_percentage", 100) for d in historical_data),
            "avg_response_p95": statistics.mean(d.get("response_time_p95", 0) for d in historical_data),
            "total_violations": sum(len(d.get("violations", [])) for d in historical_data),
            "days_with_violations": sum(1 for d in historical_data if d.get("violations"))
        }
        
        return summary
    
    def _get_recent_incidents(self) -> List[Dict]:
        """Get recent SLA incidents"""
        incidents = []
        
        for start, end in self.downtime_periods[-10:]:  # Last 10 incidents
            incidents.append({
                "type": "downtime",
                "start": datetime.fromtimestamp(start).isoformat(),
                "end": datetime.fromtimestamp(end).isoformat(),
                "duration_minutes": (end - start) / 60
            })
        
        return incidents
    
    def _save_report(self, report: Dict[str, Any]):
        """Save SLA report to file"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_file = self.data_path / f"sla_report_{timestamp}.json"
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for SLA dashboard display"""
        metrics = self.calculate_metrics()
        
        return {
            "status": metrics.status,
            "metrics": {
                "uptime": {
                    "current": metrics.uptime_percentage,
                    "target": self.targets["uptime"].target_value,
                    "unit": "%"
                },
                "availability": {
                    "current": metrics.availability_percentage,
                    "target": self.targets["availability"].target_value,
                    "unit": "%"
                },
                "response_p95": {
                    "current": metrics.response_time_p95 * 1000,  # Convert to ms
                    "target": self.targets["response_p95"].target_value * 1000,
                    "unit": "ms"
                },
                "response_p99": {
                    "current": metrics.response_time_p99 * 1000,
                    "target": self.targets["response_p99"].target_value * 1000,
                    "unit": "ms"
                },
                "error_rate": {
                    "current": metrics.error_rate,
                    "target": self.targets["error_rate"].target_value,
                    "unit": "%"
                },
                "throughput": {
                    "current": metrics.throughput_eps,
                    "target": self.targets["throughput"].target_value,
                    "unit": "eps"
                }
            },
            "violations": metrics.violations,
            "last_updated": metrics.timestamp
        }
