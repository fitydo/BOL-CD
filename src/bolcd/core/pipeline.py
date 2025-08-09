from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from .binarization import binarize_events
from .fdr import bh_qvalues
from .implication import EdgeStats, compute_all_edges
from .transitive_reduction import transitive_reduction


@dataclass
class GraphEdge:
    src: str
    dst: str
    n_src1: int
    k_counterex: int
    ci95_upper: float
    q_value: float | None


def learn_graph_from_events(
    events: Iterable[Dict[str, float]],
    thresholds: Dict[str, float],
    margin_delta: float,
    fdr_q: float,
    epsilon: float,
) -> Dict[str, Any]:
    metric_names: List[str] = list(thresholds.keys())
    values, unknowns = binarize_events(events, thresholds, margin_delta)

    # Compute pairwise stats
    raw_edges: List[EdgeStats] = compute_all_edges(metric_names, values, unknowns, epsilon)

    # Compute BH q-values for edges with p-values
    p_indices: List[int] = [i for i, e in enumerate(raw_edges) if e.p_value is not None]
    p_values: List[float] = [raw_edges[i].p_value or 1.0 for i in p_indices]
    q_values: List[float] = bh_qvalues(p_values) if p_values else []
    q_map: Dict[Tuple[str, str], float] = {}
    for idx, q in zip(p_indices, q_values):
        key = (raw_edges[idx].src, raw_edges[idx].dst)
        q_map[key] = q

    # Select edges
    accepted_pairs: List[Tuple[str, str]] = []
    edge_detail: Dict[Tuple[str, str], GraphEdge] = {}
    for e in raw_edges:
        key = (e.src, e.dst)
        q_val = q_map.get(key)
        accept = False
        if e.k_counterex == 0:
            # Rule-of-Three
            accept = e.ci95_upper <= epsilon
        else:
            # BH threshold
            accept = (q_val is not None) and (q_val <= fdr_q)
        if accept:
            accepted_pairs.append((e.src, e.dst))
            edge_detail[key] = GraphEdge(
                src=e.src,
                dst=e.dst,
                n_src1=e.n_src1,
                k_counterex=e.k_counterex,
                ci95_upper=e.ci95_upper,
                q_value=q_val,
            )

    # Transitive reduction on accepted pairs
    reduced_pairs = transitive_reduction(accepted_pairs)

    nodes = list({n for pair in reduced_pairs for n in pair})
    edges: List[Dict[str, Any]] = []
    for u, v in reduced_pairs:
        ge = edge_detail[(u, v)]
        edges.append(asdict(ge))

    return {"nodes": nodes, "edges": edges}


def generate_synthetic_events(metric_names: Sequence[str], n: int = 1200) -> List[Dict[str, float]]:
    """
    Generate synthetic events inducing a DAG X->Y->Z with zero counterexamples for
    X->Y and Y->Z (and thus X->Z), while ensuring reverse directions have counterexamples.
    """
    if len(metric_names) < 3:
        metric_names = list(metric_names) + [f"m{i}" for i in range(3 - len(metric_names))]
    m0, m1, m2 = metric_names[:3]

    events: List[Dict[str, float]] = []

    n1 = n // 2   # X=1,Y=1,Z=1
    n2 = n // 3   # X=0,Y=1,Z=1 (break Y->X)
    n3 = n // 6   # X=0,Y=0,Z=1 (break Z->Y and Z->X)
    total = n1 + n2 + n3
    n4 = max(0, n - total)  # X=0,Y=0,Z=0

    for _ in range(n1):
        events.append({m0: 1.0, m1: 1.0, m2: 1.0})
    for _ in range(n2):
        events.append({m0: 0.0, m1: 1.0, m2: 1.0})
    for _ in range(n3):
        events.append({m0: 0.0, m1: 0.0, m2: 1.0})
    for _ in range(n4):
        events.append({m0: 0.0, m1: 0.0, m2: 0.0})

    # Fill other metrics (if any) with zeros to avoid creating spurious implications
    if len(metric_names) > 3:
        for ev in events:
            for m in metric_names[3:]:
                ev[m] = 0.0

    return events
