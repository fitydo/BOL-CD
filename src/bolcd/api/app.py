from __future__ import annotations

 
import json
import base64
from time import monotonic
import uuid
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

import yaml
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

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

app = FastAPI(title="ChainLite API (BOL‑CD for SOC)", version="1.0.0")
install_middlewares(app)
app.include_router(dashboard_router)

# Secure defaults for CORS (configurable via env)
cors_origins = os.getenv("BOLCD_CORS_ORIGINS", "*")
cors_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
cors_headers = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)

CONFIG_DIR = Path(os.getenv("BOLCD_CONFIG_DIR") or (Path(__file__).resolve().parents[3] / "configs"))
LOG_DIR = Path(os.getenv("BOLCD_LOG_DIR") or (Path(__file__).resolve().parents[3] / "logs"))
AUDIT_JSONL = LOG_DIR / "audit.jsonl"
AUDIT_SQLITE = LOG_DIR / "audit.sqlite"
use_sqlite = True
try:
    # Prefer SQLite; fallback to JSONL if sqlite unavailable for any reason
    AUDIT_STORE = SQLiteAuditStore(AUDIT_SQLITE)
except Exception:  # pragma: no cover
    AUDIT_STORE = JSONLAuditStore(AUDIT_JSONL)
# Optional security toggles
REQUIRE_HTTPS = os.getenv("BOLCD_REQUIRE_HTTPS", "0").strip() in {"1", "true", "True"}
HSTS_ENABLED = os.getenv("BOLCD_HSTS_ENABLED", "0").strip() in {"1", "true", "True"}


# Metrics
REGISTRY = CollectorRegistry()
REQ_COUNT = Counter("bolcd_requests_total", "Total API requests", ["path"], registry=REGISTRY)
LAST_RECOMPUTE_EDGES = Gauge("bolcd_last_recompute_edges", "Edges in last union graph", registry=REGISTRY)
HTTP_REQUEST_DURATION = Histogram(
    "bolcd_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["path"],
    registry=REGISTRY,
)
HTTP_REQUESTS_TOTAL = Counter(
    "bolcd_http_requests_total",
    "HTTP requests by path and status",
    ["path", "code"],
    registry=REGISTRY,
)

# Expose latest daily A/B effects as Prometheus metrics (read from /reports)
BOLCD_REPORTS_DIR = Path(os.getenv("BOLCD_REPORTS_DIR", "/reports"))
AB_REDUCTION_COUNT = Gauge("bolcd_ab_reduction_by_count", "Reduction by count for latest daily AB", registry=REGISTRY)
AB_REDUCTION_UNIQUE = Gauge("bolcd_ab_reduction_by_unique", "Reduction by unique for latest daily AB", registry=REGISTRY)
AB_SUPPRESSED_COUNT = Gauge("bolcd_ab_suppressed_count", "Suppressed count for latest daily AB", registry=REGISTRY)
AB_NEW_IN_B_UNIQUE = Gauge("bolcd_ab_new_in_b_unique", "Unique signatures appearing only in B (regressions) for latest daily AB", registry=REGISTRY)
AB_NEW_IN_B_COUNT = Gauge("bolcd_ab_new_in_b_count", "Total events counted for signatures appearing only in B (regressions) for latest daily AB", registry=REGISTRY)
AB_LAST_FILE_MTIME = Gauge("bolcd_ab_last_file_mtime", "Unix mtime of the latest daily AB JSON file", registry=REGISTRY)
RATE_LIMITED_TOTAL = Counter("bolcd_rate_limited_total", "Requests rejected due to rate limiting", ["key"], registry=REGISTRY)
RATE_ALLOWED_TOTAL = Counter("bolcd_rate_allowed_total", "Requests allowed after rate limiting", ["key"], registry=REGISTRY)


def _update_ab_metrics_from_reports() -> None:
    try:
        if not BOLCD_REPORTS_DIR.exists():
            return
        # Prefer daily files like ab_YYYY-MM-DD.json; skip weekly (ab_weekly_*)
        candidates = [
            p for p in BOLCD_REPORTS_DIR.glob("ab_*.json") if not p.name.startswith("ab_weekly_")
        ]
        if not candidates:
            return
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        data = json.loads(latest.read_text(encoding="utf-8"))
        eff = data.get("effects", {})
        AB_REDUCTION_COUNT.set(float(eff.get("reduction_by_count", 0.0)))
        AB_REDUCTION_UNIQUE.set(float(eff.get("reduction_by_unique", 0.0)))
        AB_SUPPRESSED_COUNT.set(float(eff.get("suppressed_count", 0.0)))
        eff_new_in_b_unique = eff.get("new_in_b_unique")
        eff_new_in_b_count = eff.get("new_in_b_count")
        if eff_new_in_b_unique is not None:
            AB_NEW_IN_B_UNIQUE.set(float(eff_new_in_b_unique))
        else:
            new_in_b = data.get("top", {}).get("new_in_b", [])
            AB_NEW_IN_B_UNIQUE.set(float(len(new_in_b)))
            AB_NEW_IN_B_COUNT.set(float(sum(it.get("count", 0) for it in new_in_b)))
        if eff_new_in_b_count is not None:
            AB_NEW_IN_B_COUNT.set(float(eff_new_in_b_count))
        AB_LAST_FILE_MTIME.set(float(latest.stat().st_mtime))
    except Exception:
        # never fail metrics endpoint due to parsing errors
        return


@app.middleware("http")
async def collect_request_metrics(request: Request, call_next):
    path_template = request.scope.get("route").path if request.scope.get("route") else request.url.path
    start = datetime.now(timezone.utc)
    try:
        response = await call_next(request)
        return response
    finally:
        duration = (datetime.now(timezone.utc) - start).total_seconds()
        try:
            HTTP_REQUEST_DURATION.labels(path=path_template).observe(duration)
            REQ_COUNT.labels(path=path_template).inc()
            status_code = request.scope.get("aws.event", {}).get("status") if False else None  # placeholder
            # Use response status when available
            code = str(getattr(locals().get("response", None), "status_code", 0) or 0)
            HTTP_REQUESTS_TOTAL.labels(path=path_template, code=code).inc()
        except Exception:
            pass


@app.middleware("http")
async def security_headers_and_redirects(request: Request, call_next):
    # Enforce HTTPS if behind ingress/SSL-termination
    if REQUIRE_HTTPS:
        proto = request.headers.get("X-Forwarded-Proto") or request.url.scheme
        if proto != "https":
            # 308 redirect to https
            https_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=308)
    response = await call_next(request)
    # Set basic security headers
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if HSTS_ENABLED:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


def _daily_ab_json_candidates() -> List[Path]:
    if not BOLCD_REPORTS_DIR.exists():
        return []
    return [p for p in BOLCD_REPORTS_DIR.glob("ab_*.json") if not p.name.startswith("ab_weekly_")]


def _latest_daily_ab_json() -> Path | None:
    candidates = _daily_ab_json_candidates()
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _daily_ab_json_for_date(date_str: str) -> Path | None:
    # Prefer keys variant if exists
    keys = BOLCD_REPORTS_DIR / f"ab_{date_str}_keys.json"
    if keys.exists():
        return keys
    plain = BOLCD_REPORTS_DIR / f"ab_{date_str}.json"
    return plain if plain.exists() else None


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
async def metrics() -> Response:
    _update_ab_metrics_from_reports()
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root() -> RedirectResponse:
    # Redirect to the minimal dashboard for convenience
    return RedirectResponse(url="/dashboard")


@app.post("/api/encode", response_model=EncodeResponse)
async def encode(req: EncodeRequest, request: Request) -> EncodeResponse:
    from bolcd.core import binarize_events

    REQ_COUNT.labels(path="/api/encode").inc()
    values, _unknowns = binarize_events(req.events, req.thresholds, req.margin_delta)
    vectors = ["0b" + format(v, "b") for v in values]
    return EncodeResponse(vectors=vectors)


# --------- Simple token-bucket rate limiting (optional) ---------
_rate_limit_enabled = (os.getenv("BOLCD_RATE_LIMIT_ENABLED", "1").strip() in {"1", "true", "True"})
_rate_limit_rps = float(os.getenv("BOLCD_RATE_LIMIT_RPS", "10"))
_rate_limit_burst = float(os.getenv("BOLCD_RATE_LIMIT_BURST", "20"))
_buckets: Dict[str, Dict[str, float]] = {}


def _rate_limit_allow(key: str) -> bool:
    if not _rate_limit_enabled:
        return True
    now = monotonic()
    bucket = _buckets.setdefault(key, {"tokens": _rate_limit_burst, "ts": now})
    # refill
    elapsed = now - bucket["ts"]
    bucket["ts"] = now
    bucket["tokens"] = min(_rate_limit_burst, bucket["tokens"] + elapsed * _rate_limit_rps)
    if bucket["tokens"] >= 1.0:
        bucket["tokens"] -= 1.0
        return True
    return False


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Exempt health/metrics/dashboard
    path = request.url.path
    if not _rate_limit_enabled or path in {"/livez", "/readyz", "/metrics", "/", "/dashboard"}:
        return await call_next(request)
    api_key = request.headers.get("X-API-Key", "anonymous")
    allowed = _rate_limit_allow(api_key)
    tokens = _buckets.get(api_key, {}).get("tokens", -1.0)
    logging.info(
        "rate_limit_decision",
        extra={"path": path, "key": api_key, "allowed": allowed, "tokens": round(tokens, 3)},
    )
    if allowed:
        RATE_ALLOWED_TOTAL.labels(key=api_key).inc()
        return await call_next(request)
    RATE_LIMITED_TOTAL.labels(key=api_key).inc()
    return JSONResponse({"detail": "rate_limited"}, status_code=429)


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


@app.get("/api/audit/verify")
async def audit_verify(_: None = Depends(verify_role("viewer"))) -> Any:
    REQ_COUNT.labels(path="/api/audit/verify").inc()
    try:
        return AUDIT_STORE.verify_chain()
    except Exception:
        return JSONResponse({"ok": False, "error": "verify_failed"}, status_code=500)


@app.get("/api/reports/daily/latest")
async def reports_daily_latest(_: None = Depends(verify_role("viewer"))) -> Any:
    REQ_COUNT.labels(path="/api/reports/daily/latest").inc()
    p = _latest_daily_ab_json()
    if not p:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/api/reports/daily/{date}")
async def reports_daily_by_date(date: str, _: None = Depends(verify_role("viewer"))) -> Any:
    REQ_COUNT.labels(path="/api/reports/daily/{date}").inc()
    p = _daily_ab_json_for_date(date)
    if not p:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return json.loads(p.read_text(encoding="utf-8"))


class WritebackRequest(BaseModel):
    target: str
    rules: List[Dict[str, Any]]
    dry_run: bool = True


@app.post("/api/siem/writeback")
async def siem_writeback(req: WritebackRequest, request: Request, _: None = Depends(verify_role("admin"))) -> Dict[str, Any]:
    REQ_COUNT.labels(path="/api/siem/writeback").inc()
    actor = request.headers.get("X-API-Key", "anonymous")
    if req.dry_run:
        example = req.rules[0] if req.rules else {}
        AUDIT_STORE.append(actor=str(actor), action="siem_writeback_dry_run", diff={"target": req.target, "rules": len(req.rules), "example": example})
        return {"status": "dry-run", "target": req.target, "rules": len(req.rules), "example": example}
    conn = make_connector(req.target)
    result = conn.writeback(req.rules)
    AUDIT_STORE.append(actor=str(actor), action="siem_writeback_apply", diff={"target": req.target, "rules": len(req.rules)})
    return result


# ---------- Rules CRUD (stored under CONFIG_DIR / rules.json) ----------

RULES_PATH = CONFIG_DIR / "rules.json"


class Rule(BaseModel):
    name: str
    segment: str | None = None
    spl: str | None = None
    kql: str | None = None
    detector: Dict[str, Any] | None = None
    owner: str | None = None
    app: str | None = None


def _load_rules() -> List[Dict[str, Any]]:
    try:
        if not RULES_PATH.exists():
            return []
        data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _save_rules(rules: List[Dict[str, Any]]) -> None:
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    RULES_PATH.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")


@app.get("/api/rules")
async def list_rules(_: None = Depends(verify_role("viewer"))) -> Any:
    REQ_COUNT.labels(path="/api/rules").inc()
    return _load_rules()


@app.get("/api/rules/{name}")
async def get_rule(name: str, _: None = Depends(verify_role("viewer"))) -> Any:
    REQ_COUNT.labels(path="/api/rules/{name}").inc()
    rules = _load_rules()
    for r in rules:
        if r.get("name") == name:
            return r
    return JSONResponse({"error": "not_found"}, status_code=404)


@app.post("/api/rules")
async def create_rule(rule: Rule, request: Request, _: None = Depends(verify_role("admin"))) -> Any:
    REQ_COUNT.labels(path="/api/rules").inc()
    rules = _load_rules()
    if any(r.get("name") == rule.name for r in rules):
        return JSONResponse({"error": "conflict"}, status_code=409)
    rules.append(rule.model_dump())
    _save_rules(rules)
    AUDIT_STORE.append(actor=request.headers.get("X-API-Key", "anonymous"), action="rule_create", diff=rule.model_dump())
    return rule.model_dump()


@app.put("/api/rules/{name}")
async def update_rule(name: str, rule: Rule, request: Request, _: None = Depends(verify_role("admin"))) -> Any:
    REQ_COUNT.labels(path="/api/rules/{name}").inc()
    rules = _load_rules()
    found = False
    for i, r in enumerate(rules):
        if r.get("name") == name:
            rules[i] = rule.model_dump()
            found = True
            break
    if not found:
        return JSONResponse({"error": "not_found"}, status_code=404)
    _save_rules(rules)
    AUDIT_STORE.append(actor=request.headers.get("X-API-Key", "anonymous"), action="rule_update", diff={"name": name, "new": rule.model_dump()})
    return rule.model_dump()


@app.delete("/api/rules/{name}")
async def delete_rule(name: str, request: Request, _: None = Depends(verify_role("admin"))) -> Any:
    REQ_COUNT.labels(path="/api/rules/{name}").inc()
    rules = _load_rules()
    new_rules = [r for r in rules if r.get("name") != name]
    if len(new_rules) == len(rules):
        return JSONResponse({"error": "not_found"}, status_code=404)
    _save_rules(new_rules)
    AUDIT_STORE.append(actor=request.headers.get("X-API-Key", "anonymous"), action="rule_delete", diff={"name": name})
    return {"status": "deleted", "name": name}


class ApplyRulesRequest(BaseModel):
    target: str
    names: List[str] | None = None
    dry_run: bool = True


@app.post("/api/rules/apply")
async def apply_rules(req: ApplyRulesRequest, request: Request, _: None = Depends(verify_role("admin"))) -> Any:
    REQ_COUNT.labels(path="/api/rules/apply").inc()
    all_rules = _load_rules()
    sel = [r for r in all_rules if (not req.names or r.get("name") in req.names)]
    if req.dry_run:
        return {"status": "dry-run", "target": req.target, "rules": len(sel), "example": sel[0] if sel else {}}
    conn = make_connector(req.target)
    res = conn.writeback(sel)
    AUDIT_STORE.append(actor=request.headers.get("X-API-Key", "anonymous"), action="rules_apply", diff={"target": req.target, "rules": len(sel)})
    return res


class GitOpsRequest(BaseModel):
    provider: str = "github"
    title: str | None = None
    base_branch: str | None = None
    branch: str | None = None
    names: List[str] | None = None


def _github_api_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def _github_create_pr_with_rules(rules: List[Dict[str, Any]], repo: str, token: str, title: str | None, base_branch: str | None, branch: str | None) -> Dict[str, Any]:
    import httpx

    base_url = f"https://api.github.com/repos/{repo}"
    headers = _github_api_headers(token)
    # Determine base branch
    if not base_branch:
        r = httpx.get(base_url, headers=headers, timeout=30)
        r.raise_for_status()
        base_branch = r.json().get("default_branch", "main")
    # Get base ref SHA
    r = httpx.get(f"{base_url}/git/ref/heads/{base_branch}", headers=headers, timeout=30)
    r.raise_for_status()
    base_sha = r.json()["object"]["sha"]
    # Create branch
    branch = branch or f"bolcd-rules-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    rr = httpx.post(f"{base_url}/git/refs", headers=headers, json={"ref": f"refs/heads/{branch}", "sha": base_sha}, timeout=30)
    # If branch exists, continue
    if rr.status_code not in (200, 201):
        try:
            rr.raise_for_status()
        except Exception:
            pass
    # Read existing file sha (if any)
    file_path = "configs/rules.json"
    fr = httpx.get(f"{base_url}/contents/{file_path}", headers=headers, params={"ref": base_branch}, timeout=30)
    sha = fr.json().get("sha") if fr.status_code == 200 else None
    content_b64 = base64.b64encode(json.dumps(rules, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii")
    # Upsert file to branch
    put_body = {"message": title or "chore(bolcd): update rules.json", "content": content_b64, "branch": branch}
    if sha:
        put_body["sha"] = sha
    prr = httpx.put(f"{base_url}/contents/{file_path}", headers=headers, json=put_body, timeout=30)
    prr.raise_for_status()
    # Create PR
    pr_title = title or "Update BOL-CD rules"
    pr = httpx.post(f"{base_url}/pulls", headers=headers, json={"title": pr_title, "base": base_branch, "head": branch}, timeout=30)
    pr.raise_for_status()
    return pr.json()


@app.post("/api/rules/gitops")
async def rules_gitops(req: GitOpsRequest, request: Request, _: None = Depends(verify_role("admin"))) -> Any:
    REQ_COUNT.labels(path="/api/rules/gitops").inc()
    all_rules = _load_rules()
    sel = [r for r in all_rules if (not req.names or r.get("name") in req.names)]
    if req.provider != "github":
        return JSONResponse({"error": "unsupported_provider"}, status_code=400)
    repo = os.getenv("BOLCD_GITHUB_REPO")
    token = os.getenv("BOLCD_GITHUB_TOKEN")
    if not repo or not token:
        return JSONResponse({"error": "missing_repo_or_token"}, status_code=400)
    pr = _github_create_pr_with_rules(sel, repo, token, req.title, req.base_branch or os.getenv("BOLCD_GITOPS_BASE_BRANCH"), req.branch)
    AUDIT_STORE.append(actor=request.headers.get("X-API-Key", "anonymous"), action="rules_gitops_pr", diff={"repo": repo, "pr": pr.get("number")})
    return {"status": "ok", "pr": {"number": pr.get("number"), "url": pr.get("html_url")}}
