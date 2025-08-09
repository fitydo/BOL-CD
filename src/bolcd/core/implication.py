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
    Compute P(K >= k | Bin(n, p0)) one-sided. Uses:
      - guards for edge cases
      - normal approximation with continuity correction for large n
      - stable upward recurrence for small n (avoids huge combs)
    """
    if n <= 0:
        return 1.0
    if p0 <= 0.0:
        return 1.0 if k <= 0 else 0.0
    if p0 >= 1.0:
        return 1.0 if k <= n else 0.0

    # For large n use normal approximation with continuity correction
    if n >= 2000:
        from math import erfc, sqrt

        mean = n * p0
        var = n * p0 * (1.0 - p0)
        if var <= 0.0:
            return 1.0 if k <= mean else 0.0
        # continuity correction: P(X >= k) ≈ 0.5 * erfc((k - 0.5 - mean) / (sqrt(2*var)))
        z = (k - 0.5 - mean) / (sqrt(var) * (2.0 ** 0.5))
        return max(0.0, min(1.0, 0.5 * erfc(z)))

    # Small n: recurrence from r=0 up to k-1 to compute CDF, then 1 - CDF
    # P(0) = (1-p)^n; P(r+1) = P(r) * (n-r)/(r+1) * p/(1-p)
    q = 1.0 - p0
    # Start with potentially tiny value; accumulate in double should be fine for n<2000
    from math import pow

    p_r = pow(q, n)
    cdf = p_r if k > 0 else 0.0
    for r in range(0, k - 1):
        # Move to r+1
        p_r *= (n - r) / (r + 1) * (p0 / q)
        cdf += p_r
        if cdf >= 1.0 - 1e-15:
            return 0.0
    tail = 1.0 - cdf
    return max(0.0, min(1.0, tail))


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
