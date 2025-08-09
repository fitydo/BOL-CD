from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Iterable, List, Set, Tuple


def _bfs_reachable(adj: Dict[str, Set[str]], src: str, dst: str) -> bool:
    if src == dst:
        return True
    visited: Set[str] = set()
    q: deque[str] = deque([src])
    while q:
        u = q.popleft()
        if u in visited:
            continue
        visited.add(u)
        for v in adj.get(u, set()):
            if v == dst:
                return True
            if v not in visited:
                q.append(v)
    return False


def transitive_reduction(edges: Iterable[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Given a DAG edges list (src,dst), remove edges that are transitively implied.
    For each edge (u,v), temporarily remove it and if reachable(u,v) then drop it.
    """
    # Build adjacency sets
    adj: Dict[str, Set[str]] = defaultdict(set)
    for u, v in edges:
        adj[u].add(v)
        adj.setdefault(v, set())

    # Work on a copy since we remove edges
    result_adj: Dict[str, Set[str]] = {u: set(vs) for u, vs in adj.items()}

    for u, vs in list(result_adj.items()):
        for v in list(vs):
            # Remove the edge (u,v) and test reachability
            result_adj[u].remove(v)
            if _bfs_reachable(result_adj, u, v):
                # keep removed (u,v)
                pass
            else:
                # restore as it is not transitively implied
                result_adj[u].add(v)

    reduced: List[Tuple[str, str]] = []
    for u, vs in result_adj.items():
        for v in vs:
            reduced.append((u, v))
    return reduced
