from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring
from typing import Any, Dict, List, Tuple


def to_graphml(graph: Dict[str, Any]) -> str:
    """
    Convert a graph dict {nodes: [str], edges: [{src, dst, n_src1, k_counterex, ci95_upper, q_value}]}
    into a minimal GraphML string.
    """
    gml = Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
    # Keys
    SubElement(gml, "key", id="d0", for="edge", attr_name="n_src1", attr_type="int")
    SubElement(gml, "key", id="d1", for="edge", attr_name="k_counterex", attr_type="int")
    SubElement(gml, "key", id="d2", for="edge", attr_name="ci95_upper", attr_type="double")
    SubElement(gml, "key", id="d3", for="edge", attr_name="q_value", attr_type="double")

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


