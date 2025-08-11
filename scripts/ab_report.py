#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


DEFAULT_EXCLUDE = {
    "_time",
    "TimeGenerated",
    "@timestamp",
    "timestamp",
    "time",
    "_raw",
    "_cd",
    "_indextime",
    "id",
}


def make_signature(row: Dict[str, Any], keys: Sequence[str] | None) -> Tuple:
    if keys:
        items = [(k, row.get(k)) for k in keys]
    else:
        items = sorted((k, v) for k, v in row.items() if k not in DEFAULT_EXCLUDE)
    return tuple(items)


def summarize(a_rows: Iterable[Dict[str, Any]], b_rows: Iterable[Dict[str, Any]], keys: Sequence[str] | None) -> Dict[str, Any]:
    a_sigs: Counter[Tuple] = Counter()
    b_sigs: Counter[Tuple] = Counter()

    a_count = 0
    for r in a_rows:
        a_sigs[make_signature(r, keys)] += 1
        a_count += 1
    b_count = 0
    for r in b_rows:
        b_sigs[make_signature(r, keys)] += 1
        b_count += 1

    a_unique = len(a_sigs)
    b_unique = len(b_sigs)

    suppressed_sigs = [s for s in a_sigs if s not in b_sigs]
    suppressed_count = sum(a_sigs[s] for s in suppressed_sigs)

    reduction_by_count = (a_count - b_count) / a_count if a_count else 0.0
    reduction_by_unique = (a_unique - b_unique) / a_unique if a_unique else 0.0

    # Top regressions (appeared only in B) and top suppressed (A only)
    new_in_b = [
        {"signature": s, "count": b_sigs[s]}
        for s in b_sigs
        if s not in a_sigs
    ]
    new_in_b.sort(key=lambda x: x["count"], reverse=True)

    top_suppressed = [
        {"signature": s, "count": a_sigs[s]}
        for s in suppressed_sigs
    ]
    top_suppressed.sort(key=lambda x: x["count"], reverse=True)

    return {
        "inputs": {
            "a_total": a_count,
            "b_total": b_count,
            "a_unique": a_unique,
            "b_unique": b_unique,
            "keys": list(keys) if keys else "(all minus common timestamp fields)",
        },
        "effects": {
            "reduction_by_count": round(reduction_by_count, 4),
            "reduction_by_unique": round(reduction_by_unique, 4),
            "suppressed_count": suppressed_count,
            "suppressed_unique": len(suppressed_sigs),
        },
        "top": {
            "suppressed": top_suppressed[:20],
            "new_in_b": new_in_b[:20],
        },
    }


def write_reports(summary: Dict[str, Any], out_prefix: Path) -> None:
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    (out_prefix.with_suffix(".json")).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    # Markdown
    md_lines = []
    eff = summary["effects"]
    inp = summary["inputs"]
    md_lines.append(f"# A/B Report ({datetime.now(timezone.utc).isoformat()})")
    md_lines.append("")
    md_lines.append(f"- A total: {inp['a_total']}")
    md_lines.append(f"- B total: {inp['b_total']}")
    md_lines.append(f"- Reduction (count): {eff['reduction_by_count']*100:.1f}%")
    md_lines.append(f"- Reduction (unique): {eff['reduction_by_unique']*100:.1f}%")
    md_lines.append(f"- Suppressed: {eff['suppressed_count']} (unique {eff['suppressed_unique']})")
    md_lines.append("")
    md_lines.append("## Top suppressed (A only)")
    for it in summary["top"]["suppressed"]:
        md_lines.append(f"- count={it['count']} sign={it['signature']}")
    md_lines.append("")
    md_lines.append("## New in B (regressions)")
    for it in summary["top"]["new_in_b"]:
        md_lines.append(f"- count={it['count']} sign={it['signature']}")
    (out_prefix.with_suffix(".md")).write_text("\n".join(md_lines), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description="Compute A/B deltas from JSONL dumps")
    p.add_argument("--a", required=True, help="Path to A (control) JSONL")
    p.add_argument("--b", required=True, help="Path to B (treatment) JSONL")
    p.add_argument("--keys", nargs="*", help="Signature keys (default: all minus timestamp common fields)")
    p.add_argument("--out-prefix", default="reports/ab_report", help="Output prefix for .json/.md")
    args = p.parse_args()

    a_rows = read_jsonl(Path(args.a))
    b_rows = read_jsonl(Path(args.b))
    summary = summarize(a_rows, b_rows, args.keys)
    write_reports(summary, Path(args.out_prefix))
    print(json.dumps(summary["effects"], ensure_ascii=False))


if __name__ == "__main__":
    main()


