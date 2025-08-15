# BOL-CD (ChainLite) — v1.0.0

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

### A/B quick report

```bash
python scripts/ab_report.py --a data/raw/splunk_A_2025-08-11.jsonl --b data/raw/splunk_B_2025-08-11.jsonl \
  --keys source severity signature rule_name --out-prefix reports/ab_2025-08-11
```
`reports/ab_*.json` と `ab_*.md` が出力され、削減率や上位の抑制カテゴリ/回帰を確認できます。

### Weekly aggregation

```bash
python scripts/ab_weekly.py \
  --prefix-a data/raw/splunk_A_ --prefix-b data/raw/splunk_B_ \
  --start 2025-08-05 --end 2025-08-11 \
  --keys source severity signature rule_name \
  --out-prefix reports/ab_weekly_2025-08-05_2025-08-11
```
CSV と Markdown を `reports/` に出力します。

## Write-back (CLI)

- Dry-run preview (no network):
  ```
  bolcd-writeback splunk --rules examples/rules.splunk.json
  bolcd-writeback sentinel --rules examples/rules.sentinel.json
  bolcd-writeback opensearch --rules examples/rules.opensearch.json
  ```
- Apply (requires env vars):
  - Splunk: `BOLCD_SPLUNK_URL`, `BOLCD_SPLUNK_TOKEN`
    - Optional scope: `BOLCD_SPLUNK_APP` (default `search`), `BOLCD_SPLUNK_OWNER` (default `nobody`)
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
  - Roles: `admin` only（`X-API-Key`の`admin`が必要）
  - Splunk saved search のスコープ: 環境変数で `BOLCD_SPLUNK_APP`/`BOLCD_SPLUNK_OWNER` を指定可能。ルール個別にも`{"app":"search","owner":"nobody"}`で上書き可能。
- Metrics: GET `/metrics`
- Daily AB metrics: `bolcd_ab_reduction_by_count`, `bolcd_ab_reduction_by_unique`, `bolcd_ab_suppressed_count`, `bolcd_ab_new_in_b_unique`, `bolcd_ab_new_in_b_count`, `bolcd_ab_last_file_mtime`
- RBAC: add `X-API-Key` header after exporting `BOLCD_API_KEYS="key1:viewer,key2:operator,key3:admin"`

### Rules CRUD & GitOps

- Storage: `configs/rules.json`（`BOLCD_CONFIG_DIR`で上書き可）
- Endpoints:
  - GET `/api/rules` / `/api/rules/{name}`（viewer）
  - POST `/api/rules`、PUT `/api/rules/{name}`、DELETE `/api/rules/{name}`（admin）
  - POST `/api/rules/apply`（admin、`{"target":"splunk","names":["rule1"],"dry_run":true}`）
  - POST `/api/rules/gitops`（admin）: ルールをPR化
    - 環境変数: `BOLCD_GITHUB_REPO=owner/repo`, `BOLCD_GITHUB_TOKEN=<PAT>`, 任意`BOLCD_GITOPS_BASE_BRANCH=main`


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
  - Alerts: set `monitor.alertsEnabled: true` to create `PrometheusRule`
  - Thresholds:
    - `monitor.alerts.p95Ms` (default `0.1` seconds)
    - `monitor.alerts.http.errorRate5xx` (default `0.01`)
    - `monitor.alerts.http.errorRate4xx` (default `0.05`)
    - `monitor.alerts.http.errorRate429` (default `0.02`)
    - `monitor.alerts.rateLimit.enabled` / `monitor.alerts.rateLimit.increase5m`
  - Metrics used:
    - Latency: `bolcd_http_request_duration_seconds_bucket` with p95
    - Error rate: `bolcd_http_requests_total` by `code`
  - Grafana dashboard (optional): set `monitor.grafana.enabled: true` to create a ConfigMap labeled `grafana_dashboard: "1"` (folder via `monitor.grafana.folder`)
  - Ingress metrics: set `ingress.exposeMetrics: true`
  - Daily report notification: set `cron.abNotify.enabled: true` and create secret `bolcd-notify` with key `webhook`
  - ExternalSecrets: set `externalSecrets.enabled: true` and configure `secretStoreRef`/`data` to sync `bolcd-secrets`

### Daily A/B report notification (Slack/Webhook)

```
kubectl create secret generic bolcd-notify \
  --from-literal=webhook='https://hooks.slack.com/services/XXX/YYY/ZZZ' \
  -n <namespace>

helm upgrade --install bolcd ./deploy/helm -n <namespace> -f deploy/helm/values-prod.yaml --wait
```

CronJob `bolcd-ab-notify` will post the latest `/reports/ab_$(date +%F)_keys.md` (fallback: `ab_$(date +%F).md`).

Endpoints are under `/api/*` (see `api/openapi.yaml`).
