from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from bolcd.connectors.factory import make_connector


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Write back rules to SIEM (Splunk/Sentinel/OpenSearch)")
    p.add_argument("target", choices=["splunk", "sentinel", "opensearch"], help="write-back destination")
    p.add_argument("--rules", type=Path, required=True, help="JSON file: [{name:..., spl|kql|query:...}]")
    p.add_argument("--apply", action="store_true", help="execute write-back (default: dry-run)")
    args = p.parse_args(argv)

    rules = json.loads(args.rules.read_text(encoding="utf-8"))
    if not args.apply:
        print(json.dumps({"status": "dry-run", "target": args.target, "rules": len(rules), "example": rules[0] if rules else {}}, ensure_ascii=False, indent=2))
        return 0

    conn = make_connector(args.target)
    res = conn.writeback(rules)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
