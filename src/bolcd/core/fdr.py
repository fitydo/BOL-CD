from __future__ import annotations

from typing import Iterable, List, Tuple


def bh_qvalues(p_values: Iterable[float]) -> List[float]:
    """
    Compute BH q-values (FDR adjusted p-values).
    Returns list of same length as p_values preserving input order.
    """
    ps = list(p_values)
    m = len(ps)
    indexed = sorted(enumerate(ps), key=lambda t: t[1])
    q_by_rank: List[Tuple[int, float]] = []
    min_q = 1.0
    for rank, (idx, p) in enumerate(indexed, start=1):
        q = p * m / rank
        if q < min_q:
            min_q = q
        q_by_rank.append((idx, min_q))
    # Map back, ensuring monotonicity when mapping original order
    out = [1.0] * m
    for idx, q in q_by_rank:
        if q < out[idx]:
            out[idx] = q
    return [min(1.0, q) for q in out]
