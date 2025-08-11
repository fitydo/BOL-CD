# Spec Mapping to Implementation

- FR1 (OCSF/ECS normalization): `src/bolcd/connectors/normalize.py`
- FR2 (Binarization): `src/bolcd/core/binarization.py`
- FR3 (Counterexamples with bitset+popcnt): `src/bolcd/core/implication.py`
- FR4 (Rule-of-Three, binomial p, BH FDR): `src/bolcd/core/implication.py`, `src/bolcd/core/fdr.py`
- FR5 (Graph + Transitive Reduction): `src/bolcd/core/pipeline.py`, `src/bolcd/core/transitive_reduction.py`
- FR6 (SIEM write-back): `src/bolcd/connectors/*.py`, `src/bolcd/rules/generate.py`, `/api/siem/writeback`
- FR7 (Explainability): edges JSON includes stats; UI minimal, CLI/GraphML export available

- NFR (Observability): `/metrics` in `src/bolcd/api/app.py`; JSON audit via `src/bolcd/audit/store.py`
- Security (RBAC): `src/bolcd/api/middleware.py` with `BOLCD_API_KEYS`
- Acceptance: `scripts/acceptance_check.py` with deterministic synthetic data

Planned:
- ADR-0004 (k‑ary encoding): Proposed, not yet implemented

