from __future__ import annotations

import json
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from typing import Any, Dict, List


def to_graphml(graph: Dict[str, Any]) -> str:
    """
    Convert a graph dict {nodes: [str], edges: [{src, dst, n_src1, k_counterex, ci95_upper, q_value}]}
    into a minimal GraphML string.
    """
    gml = Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
    # Keys (GraphML requires 'for', 'attr.name', 'attr.type')
    SubElement(
        gml,
        "key",
        id="d0",
        attrib={"for": "edge", "attr.name": "n_src1", "attr.type": "int"},
    )
    SubElement(
        gml,
        "key",
        id="d1",
        attrib={"for": "edge", "attr.name": "k_counterex", "attr.type": "int"},
    )
    SubElement(
        gml,
        "key",
        id="d2",
        attrib={"for": "edge", "attr.name": "ci95_upper", "attr.type": "double"},
    )
    SubElement(
        gml,
        "key",
        id="d3",
        attrib={"for": "edge", "attr.name": "q_value", "attr.type": "double"},
    )

    g = SubElement(gml, "graph", edgedefault="directed")
    node_ids: List[str] = list(graph.get("nodes", []))
    for node in node_ids:
        SubElement(g, "node", id=node)

    for idx, e in enumerate(graph.get("edges", [])):
        edge_el = SubElement(g, "edge", id=f"e{idx}", source=e["src"], target=e["dst"])
        SubElement(edge_el, "data", key="d0").text = str(e.get("n_src1", 0))
        SubElement(edge_el, "data", key="d1").text = str(e.get("k_counterex", 0))
        SubElement(edge_el, "data", key="d2").text = str(e.get("ci95_upper", 0.0))
        qv = e.get("q_value")
        SubElement(edge_el, "data", key="d3").text = "" if qv is None else str(qv)

    return tostring(gml, encoding="unicode")


def write_graph_files(graph: Dict[str, Any], out_dir: Path) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "graph.json"
    graphml_path = out_dir / "graph.graphml"
    json_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    graphml_path.write_text(to_graphml(graph), encoding="utf-8")
    return {"json": json_path, "graphml": graphml_path}


