from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


@dataclass
class SynthSpec:
    seed: int = 42
    d: int = 100
    n: int = 50_000
    eta: float = 0.005
    q: float = 0.05
    mask_unknown: float = 0.03


def read_segments(config_path: Path) -> List[Tuple[str, List[str]]]:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    pairs: List[Tuple[str, List[str]]] = []
    for seg in cfg.get("segments", []):
        key = seg.get("key")
        values = seg.get("values", [])
        if key and values:
            pairs.append((key, list(values)))
    return pairs


def build_ground_truth(d: int, rng: random.Random) -> Dict[str, Any]:
    nodes = [f"m{i}" for i in range(d)]
    edges: List[Tuple[str, str]] = []
    for k in range(d // 3):
        a, b, c = f"m{3*k}", f"m{3*k+1}", f"m{3*k+2}"
        edges.append((a, b))
        edges.append((b, c))
    # 10% confounders between disjoint nodes when possible
    num_confounders = max(1, d // 10)
    used: set[str] = set()
    for _ in range(num_confounders):
        u = rng.choice(nodes)
        a_idx = rng.randrange(0, d // 3) * 3
        a, c = f"m{a_idx}", f"m{a_idx+2}"
        if u in {a, c}:
            continue
        edges.append((u, a))
        edges.append((u, c))
        used.update({u, a, c})
    return {"nodes": nodes, "edges": edges}


def generate_events_for_segment(spec: SynthSpec, gt_edges: List[Tuple[str, str]], rng: random.Random) -> List[Dict[str, Any]]:
    # Determine root probabilities per segment
    p_root = rng.uniform(0.10, 0.30)
    parents: Dict[str, List[str]] = {}
    for x, y in gt_edges:
        parents.setdefault(y, []).append(x)

    events: List[Dict[str, Any]] = []
    for _ in range(spec.n):
        ev: Dict[str, Any] = {}
        # Roots sampled Bernoulli(p_root)
        for i in range(spec.d):
            m = f"m{i}"
            if m not in parents:
                ev[m] = 1.0 if rng.random() < p_root else 0.0
        # Propagate along edges with noise
        # Repeat a few passes to account for multi-hop dependencies
        for _pass in range(2):
            for x, y in gt_edges:
                x_val = ev.get(x, 0.0)
                if x_val >= 1.0:
                    ev[y] = 1.0 if rng.random() > spec.eta else 0.0
                else:
                    base = ev.get(y, 0.0)
                    ev[y] = 1.0 if (base >= 1.0 or rng.random() < spec.q) else 0.0
        # Unknown mask
        for i in range(spec.d):
            if rng.random() < spec.mask_unknown:
                ev[f"m{i}"] = None
        events.append(ev)
    return events


def main() -> int:
    spec = SynthSpec()
    rng = random.Random(spec.seed)
    segments_cfg = Path("configs/segments.yaml")
    seg_pairs = read_segments(segments_cfg)
    gt = build_ground_truth(spec.d, rng)

    out_dir = Path("data/synth")
    out_dir.mkdir(parents=True, exist_ok=True)
    ev_path = out_dir / "events_seed42.jsonl"
    gt_path = out_dir / "gt_graph.json"

    # Events per segment: concatenate into one file, annotate segment labels
    with ev_path.open("w", encoding="utf-8") as f:
        for key, values in seg_pairs:
            for val in values:
                seg_rng = random.Random((spec.seed << 8) ^ hash((key, val)) & 0xFFFFFFFF)
                seg_events = generate_events_for_segment(spec, gt["edges"], seg_rng)
                for ev in seg_events:
                    ev[key] = val
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    manifest = {
        "seed": spec.seed,
        "d": spec.d,
        "n_per_segment": spec.n,
        "segments": [{"key": k, "values": v} for k, v in seg_pairs],
        "ground_truth": gt,
    }
    gt_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {ev_path} and {gt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


