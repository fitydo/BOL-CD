## ADR-0007: Condensed Alerts API with False-Suppression Validation and Late Replay

Status: Accepted
Date: 2025-09-05
Decision Makers: Platform, Detection, SRE
Context: Production-grade alert reduction with explainability and safety.

---

### Context

We need to deliver a production-ready system that reduces alert fatigue while minimizing false suppression. Key requirements:
- Serve “condensed” (post-suppression) alerts in real time via API keys.
- Guarantee safety: High/Critical must not be suppressed unless there is overwhelming evidence.
- Provide full auditability and explainability for every decision.
- Detect potential false suppressions and replay (“late deliver”) them when evidence accumulates.
- Expose Prometheus metrics and operate via Cron/Helm in production.

Existing components include: AB optimizers, validation harnesses, SIEM connectors, and the FastAPI stack.

### Decision

Adopt a layered architecture with: (1) decision engine with safety guards, (2) quarantine for suppressed alerts, (3) validator for false-suppression risk, (4) late-replay reconciler, and (5) API-key protected delivery APIs.

- Data model (SQLAlchemy): `Alert`, `DecisionRecord`, `Suppressed`, `LateReplay`, `ValidationLog`.
- Decision policy with safety valves:
  - Root-pass (rules with no incoming edges deliver).
  - Allowlist (configurable rules always deliver).
  - High/Critical protection (never suppress unless very strong edge evidence and low risk).
  - Near-window check (A→B within configurable seconds and strong edge: q≤α, support≥S, lift≥L). α follows ADR-0002 (FDR BH) and defaults to q=0.01.
- False-suppression validation (combined score):
  - Severity-based (High/Critical → risk↑).
  - Temporal correlation to High/Critical events (same entity within 1h → risk↑).
  - Rarity of pattern (rare -> risk↑).
- Reconciler (Cron/Helm): moves quarantined items to `LateReplay` when TTL expires, risk is high, edge drift is detected, or severity escalates.
- API design:
  - `GET /v1/alerts?view=condensed|full|delta` (API key scopes: condensed/full/delta/admin)
  - `GET /v1/alerts/late` (late feed; add header `X-Delivered-Late: true`)
  - `GET /v1/alerts/{id}/explain` (decision + validation + audit trail)
  - `POST /v1/ingest` for PoC/testing only (admin scope)
- Observability: Prometheus counters/gauges/histograms for suppression, late replay, validation score distributions, API latencies.

### Rationale

- Safety first: Combining hard guards (severity, allowlist, root-pass) with statistical evidence (edges) minimizes false suppression risk.
- Explainability: Every decision persists its reason, confidence, policy version, and validation scores for audits.
- Resilience: Late replay ensures suspect suppressions are eventually delivered without blocking real-time condensed delivery.
- Operability: API keys with scopes simplify producer/consumer integrations; Helm/Cron operationalizes reconciliation.

### Alternatives Considered

1) Pure ML gating without hard guards → rejected due to unacceptable false-suppression risk.
2) Rule-only suppression without validation → rejected for lack of robustness and explainability.
3) Sink-only quarantine without late replay → rejected; delays time-to-detection for borderline cases.

### Consequences

Positive:
- Significant alert reduction while maintaining safety for high-severity signals.
- Auditable decisions and reproducible behavior (policy versioning).
- Clear SLOs via metrics (`bolcd_suppress_total`, `bolcd_false_suppression_total`, `bolcd_late_replay_total`, latencies).

Negative / Risks:
- Additional storage and compute for quarantine/validation.
- False positives in correlation/rarity heuristics if context is limited.
- Operational complexity (Cron/Helm, API key management).

Mitigations:
- Start with conservative thresholds (α small, high support/lift, narrow near-window).
- Shadow-mode sampling + human review to calibrate validation weights.
- Per-tenant configuration for allowlists and severity protections.

### Implementation Notes

- Environment variables:
```
DB_URL=sqlite:///./bolcd.db
BOLCD_POLICY_ALPHA=0.01  # See ADR-0002 (FDR BH)
BOLCD_POLICY_SUPPORT_MIN=20
BOLCD_POLICY_LIFT_MIN=1.5
BOLCD_NEAR_WINDOW_SEC=3600
BOLCD_LATE_TTL_SEC=86400
BOLCD_API_KEYS='condensed:KEY1,full:KEY2,delta:KEY3,admin:KEY_ADMIN'
BOLCD_ALLOWLIST_RULES='R-KEEP-1,R-KEEP-2'
BOLCD_ROOT_PASS=true
```
- Metrics: expose `/metrics`; instrument decision, validation, and reconciler.
- Helm: add CronJob `late-reconciler` with schedule (e.g., every 15 minutes) and TTL policy.
- OpenAPI: document views, headers (`X-Delivered-Late`, `X-Policy-Version`, `X-Edge-Id`).

### Rollout Plan

1) Deploy in shadow mode (deliver everything; compute decisions/validation in background) and measure `false_suppression_rate`.
2) Enable suppression with conservative thresholds; monitor SLOs.
3) Gradually widen near-window and relax thresholds as confidence improves.
4) Enable late replay and integrate with downstream consumers.

### Open Questions

- How to calibrate correlation/rarity weights per environment/tenant?
- What backlog retention and privacy constraints apply to quarantine data?
- Which edges are “strong” across tenants vs tenant-specific?
