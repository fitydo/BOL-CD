#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


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
    from collections import Counter

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
    return {
        "a_total": a_count,
        "b_total": b_count,
        "a_unique": a_unique,
        "b_unique": b_unique,
        "reduction_by_count": round(reduction_by_count, 4),
        "reduction_by_unique": round(reduction_by_unique, 4),
        "suppressed_count": suppressed_count,
        "suppressed_unique": len(suppressed_sigs),
    }


def daterange(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def main() -> None:
    p = argparse.ArgumentParser(description="Aggregate daily A/B JSONL results into a weekly report")
    p.add_argument("--prefix-a", required=True, help="Prefix for A files, e.g., data/raw/splunk_A_")
    p.add_argument("--prefix-b", required=True, help="Prefix for B files, e.g., data/raw/splunk_B_")
    p.add_argument("--start", required=False, help="Start date YYYY-MM-DD (default: 6 days ago)")
    p.add_argument("--end", required=False, help="End date YYYY-MM-DD (default: today)")
    p.add_argument("--keys", nargs="*", help="Signature keys (optional)")
    p.add_argument("--out-prefix", default="reports/ab_weekly", help="Output prefix for .csv/.md")
    args = p.parse_args()

    today = date.today()
    start = date.fromisoformat(args.start) if args.start else (today - timedelta(days=6))
    end = date.fromisoformat(args.end) if args.end else today

    rows: List[Dict[str, Any]] = []
    for d in daterange(start, end):
        a_path = Path(f"{args.prefix_a}{d.isoformat()}.jsonl")
        b_path = Path(f"{args.prefix_b}{d.isoformat()}.jsonl")
        if not (a_path.exists() and b_path.exists()):
            continue
        summ = summarize(read_jsonl(a_path), read_jsonl(b_path), args.keys)
        rows.append({"date": d.isoformat(), **summ})

    out_prefix = Path(args.out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    # CSV
    csv_path = out_prefix.with_suffix(".csv")
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)

    # Markdown summary
    md = [f"# Weekly A/B Report ({start.isoformat()} – {end.isoformat()})", "", "|date|A|B|red(cnt)|red(unique)|suppressed|", "|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        md.append(f"|{r['date']}|{r['a_total']}|{r['b_total']}|{r['reduction_by_count']*100:.1f}%|{r['reduction_by_unique']*100:.1f}%|{r['suppressed_count']}|")
    (out_prefix.with_suffix(".md")).write_text("\n".join(md), encoding="utf-8")

    print(f"wrote {csv_path} and {out_prefix.with_suffix('.md')}")


if __name__ == "__main__":
    main()


