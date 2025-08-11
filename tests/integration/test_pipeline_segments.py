from __future__ import annotations

from bolcd.core.pipeline import learn_graphs_by_segments


def test_learn_graphs_by_segments_union_and_labels():
    events = [
        {"X": 1.0, "Y": 1.0, "seg": "A"},
        {"X": 1.0, "Y": 1.0, "seg": "A"},
        {"X": 0.0, "Y": 0.0, "seg": "A"},
        {"X": 1.0, "Y": 0.0, "seg": "B"},
        {"X": 1.0, "Y": 0.0, "seg": "B"},
        {"X": 0.0, "Y": 1.0, "seg": "B"},
    ]
    thresholds = {"X": 0.5, "Y": 0.5}

    res = learn_graphs_by_segments(
        events=events,
        thresholds=thresholds,
        margin_delta=0.0,
        fdr_q=0.05,
        epsilon=0.5,
        segment_by=["seg"],
    )

    assert "A" in res["segments"] and "B" in res["segments"]
    # edges in union carry segment field
    if res["union"]["edges"]:
        assert "segment" in res["union"]["edges"][0]
