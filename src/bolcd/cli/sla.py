"""SLA Monitoring CLI for BOL-CD"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import List

from bolcd.monitoring.sla import SLAMonitor


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SLA monitoring and reporting")
    
    subparsers = p.add_subparsers(dest="command", help="Commands")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate SLA report")
    report_parser.add_argument("--period", type=int, default=30, help="Report period in days (default: 30)")
    report_parser.add_argument("--config", type=Path, help="SLA config file (default: configs/sla.yaml)")
    report_parser.add_argument("--output", type=Path, help="Output file for report")
    report_parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Real-time SLA monitoring")
    monitor_parser.add_argument("--interval", type=int, default=60, help="Update interval in seconds (default: 60)")
    monitor_parser.add_argument("--config", type=Path, help="SLA config file")
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Get dashboard data")
    dashboard_parser.add_argument("--config", type=Path, help="SLA config file")
    dashboard_parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    
    args = p.parse_args(argv)
    
    if not args.command:
        p.print_help()
        return 1
    
    # Initialize monitor
    monitor = SLAMonitor(
        config_file=str(args.config) if hasattr(args, 'config') and args.config else None
    )
    
    if args.command == "report":
        # Generate report
        print(f"Generating SLA report for last {args.period} days...")
        report = monitor.get_sla_report(args.period)
        
        if args.format == "json":
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(report, f, indent=2)
                print(f"Report saved to: {args.output}")
            else:
                print(json.dumps(report, indent=2))
        else:
            # Text format
            print("\n=== SLA Compliance Report ===")
            print(f"Period: {report['period']['start'][:10]} to {report['period']['end'][:10]}")
            print(f"Overall Compliance: {'✅ PASS' if report['overall_compliance'] else '❌ FAIL'}")
            
            print("\nCurrent Metrics:")
            metrics = report["current_metrics"]
            print(f"  Uptime: {metrics['uptime_percentage']:.2f}%")
            print(f"  Availability: {metrics['availability_percentage']:.2f}%")
            print(f"  Response P95: {metrics['response_time_p95']*1000:.0f}ms")
            print(f"  Response P99: {metrics['response_time_p99']*1000:.0f}ms")
            print(f"  Error Rate: {metrics['error_rate']:.2f}%")
            print(f"  Throughput: {metrics['throughput_eps']:.0f} eps")
            print(f"  Status: {metrics['status'].upper()}")
            
            if metrics["violations"]:
                print("\nViolations:")
                for violation in metrics["violations"]:
                    print(f"  ⚠️  {violation}")
            
            if report["credits"]["percentage"] > 0:
                print(f"\nSLA Credits: {report['credits']['percentage']:.0f}%")
                for detail in report["credits"]["details"]:
                    print(f"  • {detail}")
            
            if args.output:
                # Save text report
                with open(args.output, "w") as f:
                    f.write("SLA Compliance Report\n")
                    f.write(f"Period: {report['period']['start'][:10]} to {report['period']['end'][:10]}\n")
                    f.write(f"Overall Compliance: {'PASS' if report['overall_compliance'] else 'FAIL'}\n\n")
                    f.write(json.dumps(report, indent=2))
                print(f"\nReport saved to: {args.output}")
    
    elif args.command == "monitor":
        # Real-time monitoring
        print("Starting SLA monitoring...")
        print(f"Update interval: {args.interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                # Simulate some requests for demo
                for _ in range(10):
                    response_time = 0.05 + (0.1 * (time.time() % 10) / 10)  # Variable response time
                    success = (time.time() % 10) > 1  # 90% success rate
                    monitor.record_request(response_time, success)
                
                # Get current metrics
                metrics = monitor.calculate_metrics()
                
                # Clear screen (works on Unix-like systems)
                print("\033[2J\033[H", end="")
                
                print("=== SLA Real-time Monitor ===")
                print(f"Status: {metrics.status.upper()}")
                print(f"Last Updated: {metrics.timestamp}")
                
                print("\nMetrics:")
                print(f"  Uptime: {metrics.uptime_percentage:.2f}%")
                print(f"  Availability: {metrics.availability_percentage:.2f}%")
                print(f"  Response P50: {metrics.response_time_p50*1000:.0f}ms")
                print(f"  Response P95: {metrics.response_time_p95*1000:.0f}ms")
                print(f"  Response P99: {metrics.response_time_p99*1000:.0f}ms")
                print(f"  Error Rate: {metrics.error_rate:.2f}%")
                print(f"  Throughput: {metrics.throughput_eps:.0f} eps")
                
                if metrics.violations:
                    print("\nActive Violations:")
                    for violation in metrics.violations:
                        print(f"  ⚠️  {violation}")
                else:
                    print("\n✅ All SLA targets met")
                
                time.sleep(args.interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
    
    elif args.command == "dashboard":
        # Get dashboard data
        data = monitor.get_dashboard_data()
        
        if args.format == "json":
            print(json.dumps(data, indent=2))
        else:
            print("=== SLA Dashboard Data ===")
            print(f"Status: {data['status'].upper()}")
            print(f"Last Updated: {data['last_updated']}")
            
            print("\nMetrics vs Targets:")
            for name, metric in data["metrics"].items():
                current = metric["current"]
                target = metric["target"]
                unit = metric["unit"]
                
                # Determine if target is met
                if name in ["uptime", "availability", "throughput"]:
                    met = current >= target
                else:  # response times, error rate
                    met = current <= target
                
                status = "✅" if met else "❌"
                print(f"  {name}: {current:.2f}{unit} (target: {target:.2f}{unit}) {status}")
            
            if data["violations"]:
                print("\nActive Violations:")
                for violation in data["violations"]:
                    print(f"  ⚠️  {violation}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
