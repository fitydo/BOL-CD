from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from bolcd.core import bh_qvalues


@settings(max_examples=50, deadline=None)
@given(st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=3, max_size=50))
def test_bh_non_decreasing_on_sorted_p(pvals):
    p = sorted(pvals)
    q = bh_qvalues(p)
    for i in range(1, len(q)):
        assert q[i] >= q[i - 1] - 1e-12
