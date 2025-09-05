# KPI Dashboard

## Purpose
Visualize 4 KPI categories (Noise/Ops/Cost/Risk) via daily updates → /metrics → Grafana.

## Input Sources
- `/reports/ab_YYYY-MM-DD.json`: A/B daily reports for Noise metrics
- `/reports/cases/*.jsonl`: Case data for Ops efficiency and Risk metrics
- Helm values: `ingestAGB/B` and `costPerGbUSD` for Cost metrics

## Update Flow
1. **Daily Cron** (`kpi-daily`): Runs `scripts/kpi/compute_kpi.py` → `/reports/kpi_YYYY-MM-DD.json`
2. **API /metrics**: Reads latest KPI JSON and exposes Prometheus metrics
3. **Grafana**: ConfigMap dashboard displays metrics

## KPI Categories

### Noise
- `bolcd_ab_reduction_by_count`: Count-based suppression effectiveness
- `bolcd_ab_reduction_by_unique`: Unique signature suppression
- `bolcd_ab_new_in_b`: New signatures appearing only in B (regressions)
- `bolcd_ab_total_alerts{arm}`: Total alerts per arm
- `bolcd_ab_unique_alerts{arm}`: Unique alerts per arm
- `bolcd_ab_duplicates{arm}`: Duplicate alerts per arm

### Ops Efficiency
- `bolcd_triage_p50_seconds`: Median triage time
- `bolcd_triage_p90_seconds`: 90th percentile triage time
- `bolcd_cases_processed_daily`: Daily case processing volume

### Cost
- `bolcd_cost_ingest_gb{arm}`: Data ingestion volume per arm
- `bolcd_cost_per_gb_usd`: Cost per GB
- `bolcd_cost_savings_usd`: Daily cost savings

### Risk
- `bolcd_backlog_untriaged`: Untriaged case backlog
- `bolcd_backlog_ratio`: Ratio of untriaged to total cases
- `bolcd_mttd_median_seconds`: Mean Time to Detection
- `bolcd_mttr_median_seconds`: Mean Time to Resolution

## Checklist
- [ ] API and Cron share same PVC `/reports`
- [ ] `/reports/ab_YYYY-MM-DD.json` generated daily
- [ ] Cases data schema: `detected_at/triaged_at/resolved_at/status`
- [ ] (Cost usage) `values.yaml` sets `ingestAGB/B` and `costPerGbUSD`
- [ ] Grafana dashboard appears and updates
- [ ] `/metrics` exposes all `bolcd_*` KPIs
