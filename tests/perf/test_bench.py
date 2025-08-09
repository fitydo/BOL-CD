from __future__ import annotations

from pathlib import Path

from bolcd.cli.bench import BenchParams, benchmark


def test_micro_bench_runs(tmp_path: Path):
    params = BenchParams(d=50, n=20000, runs=2, fdr_q=0.01, epsilon=0.02, delta=0.0)
    res = benchmark(params)
    assert res["eps_mean"] > 5000
    assert res["latency_ms_p95"] < 1000.0
