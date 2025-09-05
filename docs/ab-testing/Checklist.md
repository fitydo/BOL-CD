# AB Checklist

- [ ] Observation window fixed (UTC)
- [ ] Deterministic assignment (entity_id, rule_id, fixed salt)
- [ ] Dup key defined and versioned (rule_id, entity_id, time_bucket(60m))
- [ ] Preflight OK (`scripts/ab/ab_preflight.py`)
- [ ] Shared PVC mounted at /reports for API and Cron
- [ ] Daily JSON/MD present in /reports
- [ ] `/metrics` exposes `bolcd_ab_*`
- [ ] Dashboard SQL/KQL included in PR notes
- [ ] Rollback plan captured
