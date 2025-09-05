# AB Test Protocol (Immediate Hardening)

- Purpose: Validate suppression effects while ensuring reproducibility and auditability.
- Primary KPIs: `reduction_by_count`, `reduction_by_unique`, `new_in_b`, L1 triage time.
- Observation window: fixed, identical for A/B (e.g., UTC daily).
- Assignment: deterministic hash of `entity_id,rule_id` with fixed `salt`.
- Duplication key: `rule_id,entity_id,time_bucket(60m)`; version when changed.
- Stages: ReadOnly → Suggest → Safe-apply → Full-apply (rollback documented).

## Deterministic Assignment
- `scripts/ab/ab_split.py` assigns A/B using SHA-256(salt|stable_key) % 2.
- Key fields configurable via `--key-fields` (default: `entity_id,rule_id`).

## Daily Report
- `scripts/ab/ab_report.py` reads A/B JSONL and produces `ab_YYYY-MM-DD.json/.md`.
- Effects exported to Prometheus via `/metrics` (`bolcd_ab_*`).

## Weekly Aggregation
- `scripts/ab/ab_weekly.py` aggregates daily JSONs into a single summary JSON.

## Preflight
- `scripts/ab/ab_preflight.py` checks shared PVC, A/B balance (±5%), sample counts.

## Data Provenance
- Always attach the raw SPL/KQL/SQL used for dashboards to PR notes.
