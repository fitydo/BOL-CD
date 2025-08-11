#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable, Dict, Any

from bolcd.connectors.factory import make_connector


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch events from SIEM and write JSONL for dev-only use")
    parser.add_argument("target", choices=["splunk", "sentinel", "opensearch"], help="SIEM target")
    parser.add_argument("query", help="SPL/KQL/DSL query string to export")
    parser.add_argument("--out", dest="out", default=str(Path("data/raw/events.jsonl")), help="Output JSONL path")
    args = parser.parse_args()

    # Make connector using env vars (see README/Runbook)
    conn = make_connector(args.target, env=os.environ)

    if args.target == "splunk":
        rows = conn.ingest(args.query)
    elif args.target == "sentinel":
        rows = conn.ingest(args.query)
    else:
        # For OpenSearch we use a basic search helper in connector via ingest(query)
        rows = conn.ingest(args.query)

    out_path = Path(args.out)
    n = write_jsonl(out_path, rows)
    print(f"wrote {n} rows to {out_path}")


if __name__ == "__main__":
    main()


