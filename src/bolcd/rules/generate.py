from __future__ import annotations

from typing import Any, Dict, Iterable, List


def build_suppression_rules(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create minimal suppression rules for A->C when A->B and B->C exist.

    Returns a common rule format: {name, segment, spl|kql|detector}
    """
    edges = [(e.get("src"), e.get("dst"), e.get("segment")) for e in graph.get("edges", [])]
    by_seg: Dict[str, List[tuple[str, str]]] = {}
    for u, v, seg in edges:
        by_seg.setdefault(seg or "__all__", []).append((u, v))

    rules: List[Dict[str, Any]] = []
    for seg, ev in by_seg.items():
        pairs = set(ev)
        # For all A->B and B->C, suppress A->C
        for a, b in ev:
            for x, c in ev:
                if x == b and (a, c) in pairs and a != c:
                    name = f"bolcd_suppress_{a}_{c}_{seg}"
                    # SPL / KQL simple examples referencing fields a and c
                    spl = f"search {a}=* {c}=* | eval suppressed='via {b}'"
                    kql = f"{a}:* and {c}:* | project suppressed='via {b}'"
                    detector = {"rule": "suppress", "via": b, "src": a, "dst": c, "segment": seg}
                    rules.append({"name": name, "segment": seg, "spl": spl, "kql": kql, "detector": detector})
    return rules


