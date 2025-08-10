from __future__ import annotations

from bolcd.rules.generate import build_suppression_rules


def test_build_suppression_rules_basic():
    g = {
        "edges": [
            {"src": "A", "dst": "B", "segment": "__all__"},
            {"src": "B", "dst": "C", "segment": "__all__"},
            {"src": "A", "dst": "C", "segment": "__all__"},
        ]
    }
    rules = build_suppression_rules(g)
    assert any(r["detector"]["via"] == "B" and r["detector"]["src"] == "A" and r["detector"]["dst"] == "C" for r in rules)

