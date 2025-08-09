from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml
from fastapi import FastAPI
from pydantic import BaseModel

from bolcd.core.pipeline import generate_synthetic_events, learn_graph_from_events

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
    margin_delta: float = cfg.get("epsilon", 0.005)  # fallback; not ideal but ok for demo

    # Synthetic events to demonstrate end-to-end
    metric_names = list(thresholds.keys()) or ["X", "Y", "Z"]
    events = generate_synthetic_events(metric_names)

    graph = learn_graph_from_events(
        events=events,
        thresholds=thresholds or {m: 0.5 for m in metric_names},
        margin_delta=margin_delta,
        fdr_q=req.fdr_q,
        epsilon=req.epsilon,
    )
    # Cache last graph for /api/graph
    app.state.last_graph = graph
    return {"status": "ok", "edges": len(graph["edges"]), "nodes": len(graph["nodes"])}


@app.get("/api/graph")
async def graph(format: str = "json") -> Dict[str, Any]:
    g = getattr(app.state, "last_graph", {"nodes": [], "edges": []})
    return g


class WritebackRequest(BaseModel):
    target: str
    rules: List[Dict[str, Any]]


@app.post("/api/siem/writeback")
async def siem_writeback(req: WritebackRequest) -> Dict[str, Any]:
    return {"status": "ok", "target": req.target, "rules": len(req.rules)}
