"""ROI Report CLI for BOL-CD"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from bolcd.reports.roi import ROIReportGenerator


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate ROI (Return on Investment) reports")
    p.add_argument("--period", type=int, default=30, help="Report period in days (default: 30)")
    p.add_argument("--comparison", type=int, default=30, help="Comparison period in days (default: 30)")
    p.add_argument("--data-path", type=Path, default=Path("./data"), help="Path to data directory")
    p.add_argument("--output-path", type=Path, default=Path("./reports/roi"), help="Output directory for reports")
    p.add_argument("--analyst-rate", type=float, default=75.0, help="Analyst hourly rate in USD (default: $75)")
    p.add_argument("--investigation-time", type=float, default=15.0, help="Average investigation time per alert in minutes (default: 15)")
    p.add_argument("--incident-cost", type=float, default=50000.0, help="Average cost per incident in USD (default: $50,000)")
    p.add_argument("--solution-cost", type=float, default=5000.0, help="Monthly solution cost in USD (default: $5,000)")
    p.add_argument("--format", choices=["json", "markdown", "both"], default="both", help="Output format")
    
    args = p.parse_args(argv)
    
    # Create configuration
    config = {
        "analyst_hourly_rate": args.analyst_rate,
        "avg_investigation_time_minutes": args.investigation_time,
        "avg_incident_cost": args.incident_cost,
        "solution_cost_monthly": args.solution_cost
    }
    
    # Initialize generator
    generator = ROIReportGenerator(
        data_path=str(args.data_path),
        output_path=str(args.output_path),
        config=config
    )
    
    # Generate report
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=args.period)
    
    print(f"Generating ROI report for {args.period} days...")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    
    report = generator.generate_roi_report(
        start_date=start_date,
        end_date=end_date,
        comparison_period_days=args.comparison
    )
    
    # Output results
    if args.format in ["json", "both"]:
        output_file = args.output_path / f"roi_report_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"JSON report saved to: {output_file}")
    
    # Print summary
    summary = report["executive_summary"]
    print("\n=== ROI Report Summary ===")
    print(f"Alert Reduction: {summary['headline_metrics']['alert_reduction']}")
    print(f"Monthly Time Saved: {summary['headline_metrics']['time_saved_monthly']}")
    print(f"Monthly Cost Saved: {summary['headline_metrics']['cost_saved_monthly']}")
    print(f"ROI: {summary['headline_metrics']['roi_percentage']}")
    print(f"Payback Period: {summary['headline_metrics']['payback_period']}")
    
    print("\nKey Achievements:")
    for achievement in summary["key_achievements"]:
        print(f"  • {achievement}")
    
    print("\nRecommendations:")
    for rec in report.get("recommendations", []):
        print(f"  • {rec}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
