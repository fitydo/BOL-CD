from __future__ import annotations

from bolcd.core import binarize_events, compute_all_edges, bh_qvalues, transitive_reduction


def test_binarization_with_margin_and_unknown():
    events = [
        {"x": 0.0},
        {"x": 1.0},
        {"x": 0.49},
        {"x": 0.51},
        {"x": 0.5},
    ]
    thresholds = {"x": 0.5}
    values, unknowns = binarize_events(events, thresholds, margin_delta=0.01)
    # bits: index 0..4
    assert values[0] & (1 << 1)  # 1.0 -> 1
    assert values[0] & (1 << 3)  # 0.51 -> 1
    assert (values[0] & (1 << 0)) == 0
    assert (values[0] & (1 << 2)) == 0
    assert (values[0] & (1 << 4)) == 0
    # unknown at 0.5 exactly
    assert unknowns[0] & (1 << 4)


def test_implication_rule_of_three_and_binomial():
    # Two metrics A,B with 5 events
    events = [
        {"A": 1.0, "B": 1.0},  # A=1,B=1
        {"A": 1.0, "B": 1.0},  # A=1,B=1
        {"A": 1.0, "B": 1.0},  # A=1,B=1 (k=0)
        {"A": 0.0, "B": 1.0},  # A=0
        {"A": 1.0, "B": 0.0},  # A=1,B=0 (counterexample)
    ]
    thresholds = {"A": 0.5, "B": 0.5}
    vals, unknowns = binarize_events(events, thresholds, 0.0)
    names = list(thresholds.keys())
    edges = compute_all_edges(names, vals, unknowns, epsilon=0.005)

    # Find A->B and B->A
    a2b = [e for e in edges if e.src == "A" and e.dst == "B"][0]
    b2a = [e for e in edges if e.src == "B" and e.dst == "A"][0]

    assert a2b.n_src1 >= 3
    # A->B has one counterexample, so p_value exists
    assert a2b.k_counterex >= 1
    assert a2b.p_value is not None

    # B->A likely has k=0 or >0 depending on data; check fields presence
    assert b2a.n_src1 >= 1


def test_bh_monotonicity():
    ps = [0.001, 0.01, 0.02, 0.2]
    qs = bh_qvalues(ps)
    assert len(qs) == len(ps)
    # q-values should be non-decreasing wrt p-values order when sorted
    for i in range(1, len(qs)):
        assert qs[i] >= qs[i - 1]


def test_transitive_reduction_removes_ac_when_ab_bc_present():
    edges = [("A", "B"), ("B", "C"), ("A", "C")]
    reduced = transitive_reduction(edges)
    assert ("A", "C") not in set(reduced)
    assert ("A", "B") in set(reduced)
    assert ("B", "C") in set(reduced)
