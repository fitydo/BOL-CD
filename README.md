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

Endpoints are under `/api/*` (see `api/openapi.yaml`).
