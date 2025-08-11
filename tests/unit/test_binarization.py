from __future__ import annotations

from bolcd.core import binarize_events


def test_binarization_delta_and_unknown():
    events = [
        {"m": 0.0},   # below
        {"m": 1.0},   # above
        {"m": 0.49},  # below but near
        {"m": 0.51},  # above but near
        {"m": 0.5},   # exactly threshold -> unknown
        {},            # missing -> unknown
    ]
    thresholds = {"m": 0.5}
    values, unknowns = binarize_events(events, thresholds, margin_delta=0.01)

    v = values[0]
    u = unknowns[0]

    # indices: 0..5
    assert (v & (1 << 1)) and (v & (1 << 3))
    # unknown at exact threshold and missing
    assert (u & (1 << 4)) and (u & (1 << 5))
