from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml
from fastapi import FastAPI
from pydantic import BaseModel

from bolcd.core.pipeline import (
    generate_synthetic_events,
    learn_graphs_by_segments,
)
from bolcd.ui.graph_export import to_graphml, write_graph_files
from bolcd.io.jsonl import read_jsonl

app = FastAPI(title="ChainLite API (BOL‑CD for SOC)", version="0.1.0")

CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs"


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
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/encode", response_model=EncodeResponse)
async def encode(req: EncodeRequest) -> EncodeResponse:
    from bolcd.core import binarize_events

    values, _unknowns = binarize_events(req.events, req.thresholds, req.margin_delta)
    vectors = ["0b" + format(v, "b") for v in values]
    return EncodeResponse(vectors=vectors)


@app.post("/api/edges/recompute")
async def recompute(req: RecomputeRequest) -> Dict[str, Any]:
    thresholds_yaml = CONFIG_DIR / "thresholds.yaml"
    with thresholds_yaml.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    thresholds: Dict[str, float] = {k: v["threshold"] for k, v in cfg.get("metrics", {}).items()}
    margin_delta: float = cfg.get("epsilon", 0.005)  # fallback for demo

    # Load segmentation config if none provided
    segment_keys = req.segment_by
    seg_yaml = CONFIG_DIR / "segments.yaml"
    if not segment_keys and seg_yaml.exists():
        with seg_yaml.open("r", encoding="utf-8") as f:
            seg_cfg = yaml.safe_load(f)
        segment_keys = [s.get("key") for s in seg_cfg.get("segments", [])]

    metric_names = list(thresholds.keys()) or ["X", "Y", "Z"]

    # choose events source: JSONL file or synthetic demo
    if req.events_path:
        events = list(read_jsonl(req.events_path))
    else:
        events = generate_synthetic_events(metric_names)

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

    # Audit (in memory)
    audit = getattr(app.state, "audit", [])
    audit.append(
        {
            "ts": datetime.utcnow().isoformat() + "Z",
            "edges": len(union["edges"]),
            "nodes": len(union["nodes"]),
            "persist": outputs,
        }
    )
    app.state.audit = audit[-100:]

    return {"status": "ok", "edges": len(union["edges"]), "nodes": len(union["nodes"]), "outputs": outputs}


@app.get("/api/graph")
async def graph(format: str = "json") -> Any:
    graphs = getattr(app.state, "last_graphs", {"union": {"nodes": [], "edges": []}})
    g = graphs.get("union", {"nodes": [], "edges": []})
    if format == "graphml":
        return to_graphml(g)
    return g


@app.get("/api/audit")
async def audit() -> Any:
    return getattr(app.state, "audit", [])


class WritebackRequest(BaseModel):
    target: str
    rules: List[Dict[str, Any]]


@app.post("/api/siem/writeback")
async def siem_writeback(req: WritebackRequest) -> Dict[str, Any]:
    return {"status": "ok", "target": req.target, "rules": len(req.rules)}
