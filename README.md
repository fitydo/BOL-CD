# BOL-CD (ChainLite) — v0.2.0

Implements core algorithms and a FastAPI service per `docs/design.md` and `api/openapi.yaml`.

## Quickstart
### Reproducible Acceptance (seeded synthetic dataset)

Generate the deterministic dataset (seed=42), recompute, and run acceptance checks:

```bash
python scripts/generate_synth_dataset.py
python -m bolcd.cli.recompute --events data/synth/events_seed42.jsonl --thresholds configs/thresholds.yaml --segments configs/segments.yaml --out-json graph.json
python scripts/acceptance_check.py
```

Private/on‑prem data overrides (never in CI):

```bash
export BOLCD_ACCEPT_DATA=/secure/events.jsonl
export BOLCD_ACCEPT_GT=/secure/gt_graph.json
python scripts/acceptance_check.py
```

To strictly enforce functional gates locally (alerts/duplicates/FPR), set `ACCEPT_ENFORCE=1`.

- Install: `pip install -r requirements.txt`
- Run API: `uvicorn bolcd.api.app:app --reload --port 8080`
- Test: `pytest -q`

## Recompute (CLI)

- Sample data: `data/sample_events.jsonl`
- Thresholds: `configs/thresholds.yaml`
- Run recompute and export JSON graph:
  ```
  python -m bolcd.cli.recompute --events data/sample_events.jsonl --thresholds configs/thresholds.yaml --epsilon 0.02 --margin-delta 0.0 --fdr-q 0.01 --out-json graph.json
  ```

### Fetch real data for development (dev-only)

```bash
# Splunk example (requires env: BOLCD_SPLUNK_URL, BOLCD_SPLUNK_TOKEN)
python scripts/fetch_data.py splunk 'index=security earliest=-1d | head 10000' --out data/raw/splunk_1d.jsonl

# Sentinel example (requires env: BOLCD_SENTINEL_WORKSPACE_ID, BOLCD_AZURE_TOKEN)
python scripts/fetch_data.py sentinel 'SecurityEvent | take 10000' --out data/raw/sentinel_1d.jsonl

# OpenSearch example (requires env: BOLCD_OPENSEARCH_ENDPOINT)
python scripts/fetch_data.py opensearch '{"query":{"match_all":{}},"size":10000}' --out data/raw/os_1d.jsonl
```

Note: This script is for development only. Ensure output files under `data/raw/` are excluded from VCS.

## Write-back (CLI)

- Dry-run preview (no network):
  ```
  bolcd-writeback splunk --rules examples/rules.splunk.json
  bolcd-writeback sentinel --rules examples/rules.sentinel.json
  bolcd-writeback opensearch --rules examples/rules.opensearch.json
  ```
- Apply (requires env vars):
  - Splunk: `BOLCD_SPLUNK_URL`, `BOLCD_SPLUNK_TOKEN`
  - Sentinel: `BOLCD_AZURE_TOKEN`, `BOLCD_AZURE_SUBSCRIPTION_ID`, `BOLCD_AZURE_RESOURCE_GROUP`, `BOLCD_AZURE_WORKSPACE_NAME`, `BOLCD_SENTINEL_WORKSPACE_ID`
  - OpenSearch: `BOLCD_OPENSEARCH_ENDPOINT`, `BOLCD_OPENSEARCH_BASIC`

## API

- POST `/api/edges/recompute` with optional body:
  ```json
  { "events_path": "data/sample_events.jsonl", "persist_dir": "reports/$(date +%s)", "epsilon": 0.02 }
  ```
- GET `/api/graph?format=graphml` returns a GraphML string
- POST `/api/siem/writeback` body:
  ```json
  { "target": "splunk", "rules": [{"name":"BOLCD Test", "spl":"index=main | head 1"}], "dry_run": true }
  ```
- Metrics: GET `/metrics`
- RBAC: add `X-API-Key` header after exporting `BOLCD_API_KEYS="key1:viewer,key2:operator,key3:admin"`

## Benchmark

- `bolcd-bench --d 100 --n 100000 --runs 5 --out reports/bench.json`

## Docker

- Build & run:
  ```
  docker build -t bolcd-api:latest .
  docker run -p 8080:8080 -e BOLCD_API_KEYS="" bolcd-api:latest
  ```
- Compose:
  ```
  docker-compose up --build
  ```

## Production Deploy (Helm)

- Prereqs: Kubernetes cluster + Ingress controller
- Prod values: `deploy/helm/values-prod.yaml`
- Install:
  ```
  # Use immutable image tag from GHCR (short SHA)
  helm upgrade --install bolcd ./deploy/helm -n <namespace> -f deploy/helm/values-prod.yaml \
    --set image.tag=sha-<short-sha> --create-namespace --wait
  ```
- Optional:
  - Persistent audit logs: set `persistence.logs.enabled: true`
  - Secret-based API keys: set `apiKeysSecret.enabled: true`
  - Prometheus: set `monitor.serviceMonitorEnabled: true` when CRD exists（本番では既定で有効化）
  - Ingress metrics: set `ingress.exposeMetrics: true`

Endpoints are under `/api/*` (see `api/openapi.yaml`).
