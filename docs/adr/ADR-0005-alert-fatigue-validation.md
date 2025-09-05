# ADR-0005: Validate BOL‑CD impact on alert fatigue with real data

- Status: Accepted
- Owners: Platform + SecOps
- Date: 2025-08-17

## Context

Alert fatigue (high alert volumes, low actionability) remains a major operational burden in SOCs. We have a working A/B mechanism (daily job, Prometheus metrics, Grafana) and validated it on Splunk `_internal`. That confirmed the mechanism but not the business claim for security alerts. We need a rigorous validation on real alert indices, with stable keys, over ≥24h windows, with both workload and quality metrics.

## Decision

Run a shadow evaluation on real alert data to quantify BOL‑CD’s impact on alert fatigue, using daily A/B reports and SLO-style metrics. Make the claim only after we meet acceptance criteria below.

## Scope

- Data source: Splunk security/alert indices (e.g., `index=security`, or org‑specific alert indexes)
- Time window: continuous daily runs, minimum 24h; preferably 2–4 weeks for stability
- Compute: existing `bolcd-ab-daily` CronJob (K8s, Helm) with stable keys and production exclude rules

## Experiment setup

- A stream: baseline query (alerts as‑is)
- B stream: baseline with production suppression/exclude rules (what Ops considers noise)
- Keys (stable identity fields): `host index sourcetype source component group`
- Window: 24h (cron.daily)
- TLS: allow self‑signed initially (`verify=false`), tighten later

## Metrics (Prometheus and report JSON)

- Workload (should go down)
  - `bolcd_ab_reduction_by_count` (target: ≥ 0.6 initially; stretch ≥ 0.8)
  - `bolcd_ab_suppressed_count` (absolute event reduction)
- Quality (must remain safe)
  - `bolcd_ab_new_in_b_unique`, `bolcd_ab_new_in_b_count` (target: near 0; investigate any > 0)
  - Manual sampling of “top regressions” (report JSON: `top.new_in_b`)
- Ops (external, if available)
  - Triage latency p95, pager rate, alerts/person/day (before vs. after; or A vs. B if can be replayed)

## Acceptance criteria

- Over ≥7 consecutive days on real alert indices:
  - Suppression (reduction_by_count) ≥ 0.6 with stable variance
  - No critical regressions confirmed by sampling (new_in_b near 0, or explained benign)
  - If ops metrics available: no increase in missed/late criticals; triage effort decreases

## Instrumentation

- Daily job writes `/reports/ab_YYYY-MM-DD.json`
- Metrics exposed by API:
  - `bolcd_ab_reduction_by_count`
  - `bolcd_ab_new_in_b_unique`, `bolcd_ab_new_in_b_count`
  - `bolcd_ab_last_file_mtime`
- Grafana dashboard panels already wired to these metrics

## Deployment plan

1) Helm override for validation (24h window, real index, stable keys)
2) Verify: Prometheus targets up, daily report file present, metrics reflect new data
3) Run for ≥7 days; record daily snapshots and screenshots

## Hourly rolling validation & visualization (preview mode)

We do not need to wait full 24h to see trends. For faster feedback during setup:

- Set `hours=1` and `schedule: "5 * * * *"` to run every hour
- Metrics are overwritten each run; Grafana panels (singlestat/time series) show near‑real‑time changes
- Prometheus queries (examples):
  - `bolcd_ab_reduction_by_count`
  - `max without(instance,pod,endpoint)(bolcd_ab_reduction_by_count)` for time‑series
  - Likewise for `bolcd_ab_new_in_b_*`

Once stable, restore `hours=24` for daily cadence while keeping panels unchanged.

## Risks / mitigations

- Self‑signed TLS: start with `verify=false`, then enable `true` after CA is in place
- Key instability inflates `new_in_b`: keep keys to stable identifiers only
- Data privacy: restrict access to reports, scrub PII when exporting samples

## Rollback

- Set `cron.abDaily.enabled=false` to stop processing
- Keep last N daily reports for post‑mortem

## Follow‑ups

- Add write‑back dry‑run A/B to test suppression rule proposals
- Extend to Sentinel/OpenSearch connectors if available


