from __future__ import annotations

 
from pathlib import Path
from typing import Any, Dict, List

import yaml
from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, generate_latest

from bolcd.core.pipeline import (
    generate_synthetic_events,
    learn_graphs_by_segments,
)
from bolcd.ui.graph_export import to_graphml, write_graph_files
from bolcd.io.jsonl import read_jsonl
from bolcd.connectors.factory import make_connector
from bolcd.audit.store import JSONLAuditStore, SQLiteAuditStore
from .middleware import install_middlewares, verify_role
from bolcd.ui.dashboard import router as dashboard_router

app = FastAPI(title="ChainLite API (BOL‑CD for SOC)", version="0.1.0")
install_middlewares(app)
app.include_router(dashboard_router)

CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs"
LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
AUDIT_JSONL = LOG_DIR / "audit.jsonl"
AUDIT_SQLITE = LOG_DIR / "audit.sqlite"
use_sqlite = True
try:
    # Prefer SQLite; fallback to JSONL if sqlite unavailable for any reason
    AUDIT_STORE = SQLiteAuditStore(AUDIT_SQLITE)
except Exception:  # pragma: no cover
    AUDIT_STORE = JSONLAuditStore(AUDIT_JSONL)

# Metrics
REGISTRY = CollectorRegistry()
REQ_COUNT = Counter("bolcd_requests_total", "Total API requests", ["path"], registry=REGISTRY)
LAST_RECOMPUTE_EDGES = Gauge("bolcd_last_recompute_edges", "Edges in last union graph", registry=REGISTRY)


class EncodeRequest(BaseModel):
    events: List[Dict[str, float]]
    thresholds: Dict[str, float]
    margin_delta: float


class EncodeResponse(BaseModel):
    vectors: List[str]


class RecomputeRequest(BaseModel):
    fdr_q: float = 0.01
    epsilon: float = 0.005
    segment_by: List[str] | None = None
    events_path: str | None = None
    persist_dir: str | None = None


@app.get("/api/health")
async def health(request: Request) -> Dict[str, str]:
    REQ_COUNT.labels(path="/api/health").inc()
    return {"status": "ok"}


@app.get("/livez")
async def livez() -> Dict[str, str]:
    # Basic liveness: process is up
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> Dict[str, str]:
    # Simple readiness: app object exists and metrics registry is initialized
    _ = REGISTRY
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Any:
    return generate_latest(REGISTRY), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.post("/api/encode", response_model=EncodeResponse)
async def encode(req: EncodeRequest, request: Request) -> EncodeResponse:
    from bolcd.core import binarize_events

    REQ_COUNT.labels(path="/api/encode").inc()
    values, _unknowns = binarize_events(req.events, req.thresholds, req.margin_delta)
    vectors = ["0b" + format(v, "b") for v in values]
    return EncodeResponse(vectors=vectors)


@app.post("/api/edges/recompute")
async def recompute(req: RecomputeRequest, request: Request, _: None = Depends(verify_role("operator"))) -> Dict[str, Any]:
    REQ_COUNT.labels(path="/api/edges/recompute").inc()
    thresholds_yaml = CONFIG_DIR / "thresholds.yaml"
    with thresholds_yaml.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    thresholds: Dict[str, float] = {k: v["threshold"] for k, v in cfg.get("metrics", {}).items()}
    margin_delta: float = cfg.get("epsilon", 0.005)  # fallback for demo

    segment_keys = req.segment_by
    seg_yaml = CONFIG_DIR / "segments.yaml"
    if not segment_keys and seg_yaml.exists():
        with seg_yaml.open("r", encoding="utf-8") as f:
            seg_cfg = yaml.safe_load(f)
        segment_keys = [s.get("key") for s in seg_cfg.get("segments", [])]

    metric_names = list(thresholds.keys()) or ["X", "Y", "Z"]

    if req.events_path:
        events = list(read_jsonl(req.events_path))
    else:
        events = generate_synthetic_events(metric_names)

    # Infer thresholds for metrics present in events but missing from config
    if events:
        exclude = set(segment_keys or [])
        missing: Dict[str, float] = {}
        for ev in events[: min(1000, len(events))]:
            for k, v in ev.items():
                if k in exclude:
                    continue
                if isinstance(v, (int, float)) or v is None:
                    if k not in thresholds:
                        missing[k] = 0.5
        if missing:
            thresholds.update(missing)

    graphs = learn_graphs_by_segments(
        events=events,
        thresholds=thresholds or {m: 0.5 for m in metric_names},
        margin_delta=margin_delta,
        fdr_q=req.fdr_q,
        epsilon=req.epsilon,
        segment_by=segment_keys,
    )
    app.state.last_graphs = graphs

    union = graphs["union"]

    outputs: Dict[str, str] = {}
    if req.persist_dir:
        paths = write_graph_files(union, Path(req.persist_dir))
        outputs = {k: str(v) for k, v in paths.items()}

    LAST_RECOMPUTE_EDGES.set(len(union["edges"]))

    actor = request.headers.get("X-API-Key", "anonymous")
    AUDIT_STORE.append(
        actor=actor,
        action="recompute",
        diff={"edges": len(union["edges"]), "nodes": len(union["nodes"]), "persist": outputs},
    )

    return {"status": "ok", "edges": len(union["edges"]), "nodes": len(union["nodes"]), "outputs": outputs}


@app.get("/api/graph")
async def graph(format: str = "json") -> Any:
    REQ_COUNT.labels(path="/api/graph").inc()
    graphs = getattr(app.state, "last_graphs", {"union": {"nodes": [], "edges": []}})
    g = graphs.get("union", {"nodes": [], "edges": []})
    if format == "graphml":
        return to_graphml(g)
    return g


@app.get("/api/audit")
async def audit(_: None = Depends(verify_role("viewer"))) -> Any:
    REQ_COUNT.labels(path="/api/audit").inc()
    return AUDIT_STORE.tail(100)


class WritebackRequest(BaseModel):
    target: str
    rules: List[Dict[str, Any]]
    dry_run: bool = True


@app.post("/api/siem/writeback")
async def siem_writeback(req: WritebackRequest, _: None = Depends(verify_role("operator"))) -> Dict[str, Any]:
    REQ_COUNT.labels(path="/api/siem/writeback").inc()
    if req.dry_run:
        example = req.rules[0] if req.rules else {}
        return {"status": "dry-run", "target": req.target, "rules": len(req.rules), "example": example}
    conn = make_connector(req.target)
    result = conn.writeback(req.rules)
    return result
