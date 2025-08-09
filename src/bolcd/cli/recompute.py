from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

from bolcd.core.pipeline import learn_graph_from_events


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Recompute edges and export graph")
    p.add_argument("--events", type=Path, default=Path("data/sample_events.jsonl"))
    p.add_argument("--thresholds", type=Path, default=Path("configs/thresholds.yaml"))
    p.add_argument("--margin-delta", type=float, default=0.0)
    p.add_argument("--fdr-q", type=float, default=0.01)
    p.add_argument("--epsilon", type=float, default=0.005)
    p.add_argument("--out-json", type=Path, default=Path("graph.json"))
    args = p.parse_args(argv)

    with args.thresholds.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    thresholds: Dict[str, float] = {k: v["threshold"] for k, v in cfg.get("metrics", {}).items()}

    events = list(read_jsonl(args.events))
    g = learn_graph_from_events(
        events=events,
        thresholds=thresholds,
        margin_delta=args.margin_delta,
        fdr_q=args.fdr_q,
        epsilon=args.epsilon,
    )

    with args.out_json.open("w", encoding="utf-8") as f:
        json.dump(g, f, ensure_ascii=False, indent=2)

    print(f"Wrote {args.out_json} with {len(g['nodes'])} nodes and {len(g['edges'])} edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
