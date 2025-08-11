from __future__ import annotations

from typing import Iterable, List, Tuple


def bh_qvalues(p_values: Iterable[float]) -> List[float]:
    """
    Compute Benjamini–Hochberg (BH) q-values (FDR adjusted p-values).

    Algorithm:
      1) Sort p-values ascending with original indices
      2) Compute q_i = p_(i) * m / i for rank i
      3) Enforce monotone non-decreasing in rank via reverse cumulative minima
      4) Map back to original order
    """
    ps = list(p_values)
    m = len(ps)
    if m == 0:
        return []

    indexed = sorted(enumerate(ps), key=lambda t: t[1])  # (orig_idx, p)
    # Step 2: raw q-values by rank
    raw_q_by_rank: List[Tuple[int, float]] = []
    for rank, (orig_idx, p) in enumerate(indexed, start=1):
        q = (p * m) / rank
        raw_q_by_rank.append((orig_idx, q))

    # Step 3: reverse cumulative minima over ranks to ensure monotonicity
    # Work over the ranked order, then map back
    q_ranked: List[float] = [q for _idx, q in raw_q_by_rank]
    min_so_far = 1.0
    for i in range(m - 1, -1, -1):
        if q_ranked[i] < min_so_far:
            min_so_far = q_ranked[i]
        q_ranked[i] = min_so_far

    # Step 4: map to original order
    out = [1.0] * m
    for (orig_idx, _p), q in zip(indexed, q_ranked):
        out[orig_idx] = min(1.0, q)
    return out
