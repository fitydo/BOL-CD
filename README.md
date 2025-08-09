# BOL-CD (ChainLite)

Implements core algorithms and a FastAPI service per `docs/design.md` and `api/openapi.yaml`.

## Quickstart

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
  ```
  bolcd-writeback splunk --rules examples/rules.splunk.json --apply
  ```

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

## Benchmark

- `bolcd-bench --d 100 --n 100000 --runs 5 --out reports/bench.json`

Endpoints are under `/api/*` (see `api/openapi.yaml`).
