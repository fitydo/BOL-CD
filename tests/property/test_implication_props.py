from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from bolcd.core import binarize_events
from bolcd.core.implication import compute_all_edges


@settings(max_examples=50, deadline=None)
@given(st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=10, max_size=100))
def test_unknowns_monotonicity(values):
    # Build events for metric X around threshold 0.5
    events = [{"X": v} for v in values]
    thresholds = {"X": 0.5}
    v1, u1 = binarize_events(events, thresholds, margin_delta=0.0)
    v2, u2 = binarize_events(events, thresholds, margin_delta=0.1)  # more unknowns
    # Unknown mask should have more or equal bits set
    assert (u2[0].bit_count() >= u1[0].bit_count())


@settings(max_examples=30, deadline=None)
@given(st.integers(min_value=1, max_value=500))
def test_rule_of_three_bound_equals_3_over_n(n):
    events = [{"X": 1.0, "Y": 1.0} for _ in range(n)]
    thresholds = {"X": 0.5, "Y": 0.5}
    vals, unknowns = binarize_events(events, thresholds, 0.0)
    edges = compute_all_edges(["X", "Y"], vals, unknowns, epsilon=1.0)
    e = next(e for e in edges if e.src == "X" and e.dst == "Y")
    assert e.k_counterex == 0
    assert abs(e.ci95_upper - (3.0 / max(1, e.n_src1))) < 1e-12
