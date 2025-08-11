from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import yaml

from bolcd.core.pipeline import learn_graphs_by_segments
from bolcd.ui.graph_export import to_graphml
from bolcd.io.jsonl import read_jsonl


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Recompute edges and export graph")
    p.add_argument("--events", type=Path, default=Path("data/sample_events.jsonl"))
    p.add_argument("--thresholds", type=Path, default=Path("configs/thresholds.yaml"))
    p.add_argument("--margin-delta", type=float, default=0.0)
    p.add_argument("--fdr-q", type=float, default=0.01)
    p.add_argument("--epsilon", type=float, default=0.005)
    p.add_argument("--segments", type=Path, default=Path("configs/segments.yaml"))
    p.add_argument("--out-json", type=Path, default=Path("graph.json"))
    p.add_argument("--out-graphml", type=Path, default=None)
    args = p.parse_args(argv)

    with args.thresholds.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    thresholds: Dict[str, float] = {k: v["threshold"] for k, v in cfg.get("metrics", {}).items()}

    segment_keys: List[str] | None = None
    if args.segments.exists():
        with args.segments.open("r", encoding="utf-8") as f:
            seg_cfg = yaml.safe_load(f)
        segment_keys = [s.get("key") for s in seg_cfg.get("segments", [])]

    events = list(read_jsonl(args.events))
    # Infer thresholds for metrics present in events but missing from config
    inferred: Dict[str, float] = {}
    if events:
        # Collect candidate metric names from events (exclude segment keys)
        exclude = set(segment_keys or [])
        for ev in events[: min(1000, len(events))]:
            for k, v in ev.items():
                if k in exclude:
                    continue
                if isinstance(v, (int, float)) or v is None:
                    if k not in thresholds:
                        inferred[k] = 0.5
        if inferred:
            thresholds = {**thresholds, **inferred}
    graphs = learn_graphs_by_segments(
        events=events,
        thresholds=thresholds,
        margin_delta=args.margin_delta,
        fdr_q=args.fdr_q,
        epsilon=args.epsilon,
        segment_by=segment_keys,
    )

    with args.out_json.open("w", encoding="utf-8") as f:
        json.dump(graphs["union"], f, ensure_ascii=False, indent=2)

    if args.out_graphml:
        args.out_graphml.write_text(to_graphml(graphs["union"]), encoding="utf-8")

    print(
        f"Wrote {args.out_json} with {len(graphs['union']['nodes'])} nodes and {len(graphs['union']['edges'])} edges"
    )
    if args.out_graphml:
        print(f"Wrote {args.out_graphml} (GraphML)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
