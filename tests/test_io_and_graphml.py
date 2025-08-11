from __future__ import annotations

from pathlib import Path

from bolcd.io.jsonl import read_jsonl
from bolcd.ui.graph_export import to_graphml


def test_read_jsonl(tmp_path: Path):
    p = tmp_path / "e.jsonl"
    p.write_text('{"a":1}\n{}\n{"b":2}\n', encoding="utf-8")
    rows = list(read_jsonl(p))
    assert rows[0]["a"] == 1 and "b" in rows[2]


def test_to_graphml_minimal():
    g = {"nodes": ["X", "Y"], "edges": [{"src": "X", "dst": "Y", "n_src1": 1, "k_counterex": 0, "ci95_upper": 3.0, "q_value": None}]}
    xml = to_graphml(g)
    assert "<graphml" in xml and "<edge" in xml and "key=\"d0\"" in xml
