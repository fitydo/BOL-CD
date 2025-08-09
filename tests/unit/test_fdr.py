from __future__ import annotations

from bolcd.core import bh_qvalues


def test_bh_monotonicity_and_bounds():
    ps = [0.001, 0.01, 0.02, 0.2]
    qs = bh_qvalues(ps)
    assert len(qs) == len(ps)
    # sorted p -> non-decreasing q
    for i in range(1, len(qs)):
        assert qs[i] >= qs[i - 1] - 1e-12
    # clamp [0,1]
    assert all(0.0 <= q <= 1.0 for q in qs)
