from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_graph_artifacts() -> list[str]:
    errors: list[str] = []
    gpath = Path("graph.json")
    if gpath.exists():
        g = load_json(gpath)
        if not isinstance(g.get("nodes"), list) or not isinstance(g.get("edges"), list):
            errors.append("graph.json missing nodes/edges lists")
    gml = Path("graph.graphml")
    if gml.exists() and "<graphml" not in gml.read_text(encoding="utf-8"):
        errors.append("graph.graphml invalid")
    return errors


def check_perf_report() -> list[str]:
    errors: list[str] = []
    bench_path = Path("bench.json")
    if not bench_path.exists():
        return errors
    r = load_json(bench_path)
    eps = float(r.get("eps_mean", 0))
    p95 = float(r.get("latency_ms_p95", 1e9))
    eps_floor = float(os.environ.get("ACCEPT_EPS_FLOOR", "5000"))
    p95_ceil = float(os.environ.get("ACCEPT_P95_CEIL_MS", "50000"))
    if eps < eps_floor:
        errors.append(f"EPS below floor: {eps} < {eps_floor}")
    if p95 > p95_ceil:
        errors.append(f"p95 above ceil: {p95} > {p95_ceil}")
    return errors


def main() -> int:
    errors: list[str] = []
    errors += check_graph_artifacts()
    errors += check_perf_report()
    if errors:
        for e in errors:
            print(f"ACCEPTANCE FAIL: {e}", file=sys.stderr)
        return 1
    print("Acceptance: checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
