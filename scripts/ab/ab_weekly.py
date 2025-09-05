#!/usr/bin/env python3
import argparse
import json
import pathlib


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate daily AB json files into a weekly summary")
    ap.add_argument('--dir', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    d = pathlib.Path(args.dir)
    days = sorted(d.glob("ab_*.json"))
    totalA = totalB = uniqA = uniqB = dupA = dupB = newB = 0
    n = 0
    for p in days:
        data = json.loads(p.read_text(encoding='utf-8'))
        totalA += data["A"]["total"]
        uniqA += data["A"]["unique"]
        dupA += data["A"]["duplicates"]
        totalB += data["B"]["total"]
        uniqB += data["B"]["unique"]
        dupB += data["B"]["duplicates"]
        newB += data.get("new_in_b", 0)
        n += 1
    result = {
        "days": n,
        "A": {"total": totalA, "unique": uniqA, "duplicates": dupA},
        "B": {"total": totalB, "unique": uniqB, "duplicates": dupB},
        "reduction_by_count": (totalA - totalB) / totalA if totalA > 0 else 0.0,
        "reduction_by_unique": (uniqA - uniqB) / uniqA if uniqA > 0 else 0.0,
        "sum_new_in_b": newB,
    }
    pathlib.Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({"ok": True, "out": args.out}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


