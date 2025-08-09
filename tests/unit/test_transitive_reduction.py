from __future__ import annotations

from bolcd.core import transitive_reduction


def test_transitive_reduction_redundancy_removed():
    edges = [("A", "B"), ("B", "C"), ("A", "C")]
    reduced = transitive_reduction(edges)
    assert ("A", "C") not in set(reduced)
    assert ("A", "B") in set(reduced)
    assert ("B", "C") in set(reduced)
