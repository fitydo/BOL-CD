from __future__ import annotations

from bolcd.core import binarize_events
from bolcd.core.implication import compute_all_edges


def test_implication_counterexamples_and_rule_of_three():
    events = [
        {"A": 1.0, "B": 1.0},
        {"A": 1.0, "B": 1.0},
        {"A": 1.0, "B": 1.0},
        {"A": 0.0, "B": 1.0},
        {"A": 1.0, "B": 0.0},  # counterexample for A->B
    ]
    thresholds = {"A": 0.5, "B": 0.5}
    vals, unknowns = binarize_events(events, thresholds, 0.0)
    names = list(thresholds.keys())

    edges = compute_all_edges(names, vals, unknowns, epsilon=0.02)
    e = {(e.src, e.dst): e for e in edges}

    assert ("A", "B") in e and ("B", "A") in e
    assert e[("A", "B")].k_counterex >= 1
    # For B->A, k may be 0; if so, ci95_upper = 3/n_src1
    if e[("B", "A")].k_counterex == 0:
        assert abs(e[("B", "A")].ci95_upper - 3.0 / e[("B", "A")].n_src1) < 1e-9
