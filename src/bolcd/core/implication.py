from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class EdgeStats:
    src: str
    dst: str
    n_src1: int
    k_counterex: int
    ci95_upper: float
    p_value: float | None


def popcount(x: int) -> int:
    return x.bit_count()


def compute_counterexamples(src_bits: int, dst_bits: int, dst_unknown: int) -> int:
    """k_{i\bar{j}} = popcnt(S_i & ~S_j & ~unknown_j)."""
    return popcount(src_bits & ~dst_bits & ~dst_unknown)


def rule_of_three_upper(n_src1: int) -> float:
    """95% one-sided upper bound when k=0 counterexamples: 3/n."""
    if n_src1 <= 0:
        return float("inf")
    return 3.0 / n_src1


def one_sided_binomial_pvalue(k: int, n: int, p0: float) -> float:
    """
    Left-tail one-sided binomial p-value: P(K ≤ k | K ~ Bin(n, p0)).
    This tests H1: p < p0 (i.e., counterexample rate is smaller than tolerance),
    which is appropriate for accepting implications when k > 0 but small.
    """
    if n <= 0:
        return 1.0
    # For small p0 and moderate n we keep exact summation with early break.
    from math import comb

    cum = 0.0
    for r in range(0, k + 1):
        cum += comb(n, r) * (p0**r) * ((1 - p0) ** (n - r))
        if cum > 1 - 1e-15:
            return 1.0
    return min(1.0, max(0.0, cum))


def compute_all_edges(
    metric_names: Sequence[str],
    values_per_metric: Sequence[int],
    unknown_per_metric: Sequence[int],
    epsilon: float,
) -> List[EdgeStats]:
    """
    For each ordered pair (i, j), compute counters and tests.
    - n_src1: popcnt(S_i & ~unknown_i)
    - k: popcnt(S_i & ~S_j & ~unknown_j)
    - if k == 0: ci95_upper = 3/n_src1 (Rule-of-Three), p_value=None
    - else: ci95_upper=None, p_value from one-sided binomial under p0=epsilon
    """
    d = len(metric_names)
    edges: List[EdgeStats] = []
    not_unknown_src = [~u for u in unknown_per_metric]
    for i in range(d):
        src_bits = values_per_metric[i]
        src_n = popcount(src_bits & not_unknown_src[i])
        if src_n == 0:
            continue
        for j in range(d):
            if i == j:
                continue
            dst_bits = values_per_metric[j]
            dst_unk = unknown_per_metric[j]
            k = compute_counterexamples(src_bits, dst_bits, dst_unk)
            if k == 0:
                ci = rule_of_three_upper(src_n)
                edges.append(
                    EdgeStats(
                        src=metric_names[i],
                        dst=metric_names[j],
                        n_src1=src_n,
                        k_counterex=0,
                        ci95_upper=ci,
                        p_value=None,
                    )
                )
            else:
                p = one_sided_binomial_pvalue(k, src_n, epsilon)
                edges.append(
                    EdgeStats(
                        src=metric_names[i],
                        dst=metric_names[j],
                        n_src1=src_n,
                        k_counterex=k,
                        ci95_upper=float("nan"),
                        p_value=p,
                    )
                )
    return edges
