from __future__ import annotations

from typing import Dict, Iterable, List, Tuple


def binarize_events(
    events: Iterable[Dict[str, float]],
    thresholds: Dict[str, float],
    margin_delta: float,
) -> Tuple[List[int], List[int]]:
    """
    Binarize events to 1/0 with an unknown mask (⊥) using margin δ around thresholds a_i.

    For a metric x_i and threshold a_i:
      - 1 if x_i >= a_i + δ
      - 0 if x_i <= a_i - δ
      - unknown otherwise (mask bit = 1)

    Returns tuple (values_bitset_per_metric, unknown_mask_per_metric), each list of bitsets
    packed into Python ints with bit k representing event index k.
    """
    metrics = list(thresholds.keys())
    n = 0
    events_list = []
    for ev in events:
        events_list.append(ev)
        n += 1

    values: List[int] = [0] * len(metrics)
    unknowns: List[int] = [0] * len(metrics)

    for bit_index, ev in enumerate(events_list):
        bit = 1 << bit_index
        for m_index, metric in enumerate(metrics):
            a_i = thresholds[metric]
            x = ev.get(metric)
            if x is None:
                unknowns[m_index] |= bit
                continue
            # Per docs/design.md we treat boundary with margin δ as unknown (Kleene logic)
            if x >= a_i + margin_delta:
                values[m_index] |= bit
            elif x <= a_i - margin_delta:
                # explicitly 0 → nothing to set in values
                pass
            else:
                unknowns[m_index] |= bit

    return values, unknowns
