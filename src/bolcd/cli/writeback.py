from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from bolcd.connectors.factory import make_connector
from bolcd.rules.generate import build_suppression_rules


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Write back rules to SIEM (Splunk/Sentinel/OpenSearch)")
    p.add_argument("target", choices=["splunk", "sentinel", "opensearch"], help="write-back destination")
    p.add_argument("--rules", type=Path, required=False, help="JSON rules file; if omitted, derive from graph.json")
    p.add_argument("--graph", type=Path, default=Path("graph.json"), help="Graph JSON to derive rules when --rules missing")
    p.add_argument("--apply", action="store_true", help="execute write-back (default: dry-run)")
    args = p.parse_args(argv)

    if args.rules and args.rules.exists():
        rules = json.loads(args.rules.read_text(encoding="utf-8"))
    else:
        g = json.loads(args.graph.read_text(encoding="utf-8"))
        rules = build_suppression_rules(g)
    if not args.apply:
        print(json.dumps({"status": "dry-run", "target": args.target, "rules": len(rules), "example": rules[0] if rules else {}}, ensure_ascii=False, indent=2))
        return 0

    conn = make_connector(args.target)
    res = conn.writeback(rules)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
