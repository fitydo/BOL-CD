from __future__ import annotations

from bolcd.core.pipeline import (
    generate_synthetic_events,
    learn_graphs_by_segments,
    learn_graph_from_events,
)


def test_learn_graph_and_tr():
    metrics = ["X", "Y", "Z"]
    thresholds = {m: 0.5 for m in metrics}
    events = generate_synthetic_events(metrics, n=300)
    g = learn_graph_from_events(
        events=events,
        thresholds=thresholds,
        margin_delta=0.0,
        fdr_q=0.01,
        epsilon=0.02,  # 3/200 ≈ 0.015 <= 0.02, accept X->Y and Y->Z
    )
    edges = {(e["src"], e["dst"]) for e in g["edges"]}
    # Minimal chain X->Y and Y->Z should exist; X->Z should not after TR
    assert ("X", "Y") in edges
    assert ("Y", "Z") in edges
    assert ("X", "Z") not in edges


def test_learn_graph_by_segment_splits_graphs():
    events = [
        {"X": 1.0, "Y": 1.0, "seg": "A"},
        {"X": 1.0, "Y": 1.0, "seg": "A"},
        {"X": 0.0, "Y": 0.0, "seg": "A"},
        {"X": 1.0, "Y": 0.0, "seg": "B"},
        {"X": 1.0, "Y": 0.0, "seg": "B"},
        {"X": 0.0, "Y": 1.0, "seg": "B"},
    ]
    thresholds = {"X": 0.5, "Y": 0.5}
    result = learn_graphs_by_segments(
        events=events,
        thresholds=thresholds,
        margin_delta=0.0,
        fdr_q=0.05,
        epsilon=0.5,
        segment_by=["seg"],
    )
    # Ensure two segments exist
    seg_keys = set(result["segments"].keys())
    assert "A" in seg_keys and "B" in seg_keys
    # Each segment has its own nodes/edges
    assert isinstance(next(iter(result["segments"].values())), dict)
