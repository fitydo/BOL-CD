from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from bolcd.core.pipeline import generate_synthetic_events, learn_graph_from_events


@dataclass
class BenchParams:
    d: int
    n: int
    runs: int
    fdr_q: float
    epsilon: float
    delta: float


def run_once(params: BenchParams) -> Dict[str, Any]:
    metrics = [f"m{i}" for i in range(params.d)]
    thresholds = {m: 0.5 for m in metrics}
    events = generate_synthetic_events(metrics, n=params.n)
    t0 = time.perf_counter()
    g = learn_graph_from_events(events, thresholds, params.delta, params.fdr_q, params.epsilon)
    t1 = time.perf_counter()
    elapsed_s = t1 - t0
    eps = params.n / elapsed_s if elapsed_s > 0 else float("inf")
    return {"elapsed_s": elapsed_s, "eps": eps, "nodes": len(g["nodes"]), "edges": len(g["edges"]) }


def benchmark(params: BenchParams) -> Dict[str, Any]:
    samples = [run_once(params) for _ in range(params.runs)]
    eps_list = [s["eps"] for s in samples]
    lat_ms = [s["elapsed_s"] * 1000.0 for s in samples]
    return {
        "params": params.__dict__,
        "eps_mean": statistics.mean(eps_list),
        "eps_p95": statistics.quantiles(eps_list, n=20)[-1] if len(eps_list) >= 2 else eps_list[0],
        "latency_ms_mean": statistics.mean(lat_ms),
        "latency_ms_p95": statistics.quantiles(lat_ms, n=20)[-1] if len(lat_ms) >= 2 else lat_ms[0],
        "runs": samples,
    }


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run synthetic performance benchmark")
    p.add_argument("--d", type=int, default=100)
    p.add_argument("--n", type=int, default=100_000)
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--fdr-q", type=float, default=0.01)
    p.add_argument("--epsilon", type=float, default=0.005)
    p.add_argument("--delta", type=float, default=0.0)
    p.add_argument("--out", type=Path, default=Path("reports/bench.json"))
    args = p.parse_args(argv)

    params = BenchParams(d=args.d, n=args.n, runs=args.runs, fdr_q=args.fdr_q, epsilon=args.epsilon, delta=args.delta)
    res = benchmark(params)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote benchmark report to {args.out}")
    print(f"EPS mean={res['eps_mean']:.1f}, p95={res['eps_p95']:.1f}; latency p95={res['latency_ms_p95']:.1f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
