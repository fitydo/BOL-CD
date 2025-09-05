#!/usr/bin/env python3
import argparse
import json
import pathlib
import datetime
from dateutil import parser as dtp


def load_jsonl(p: str):
    with open(p, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def bucket(ts_iso: str, minutes: int) -> str:
    dt = dtp.parse(ts_iso)
    minute = (dt.minute // minutes) * minutes
    dtb = dt.replace(second=0, microsecond=0, minute=minute)
    return dtb.isoformat()


def stats(recs, dup_keys, bucket_minutes):
    total = 0
    uniq = set()
    entities = set()
    rules = set()
    for r in recs:
        total += 1
        ts = r.get('ts') or r.get('@timestamp') or r.get('time')
        tb = r.get('time_bucket') or (bucket(ts, bucket_minutes) if ts else '')
        key = []
        for k in dup_keys:
            key.append(tb if k == 'time_bucket' else str(r.get(k, '')))
        uniq.add(tuple(key))
        if 'entity_id' in r:
            entities.add(r['entity_id'])
        if 'rule_id' in r:
            rules.add(r['rule_id'])
    return {
        "total": total,
        "unique": len(uniq),
        "duplicates": max(0, total - len(uniq)),
        "entities": len([x for x in entities if x]),
        "rules": len([x for x in rules if x]),
        "_uniq_set": uniq,
    }


def mk_md(date_label, a, b, reduction_count, reduction_unique, new_in_b):
    md = []
    md.append(f"# A/B 日次レポート ({date_label})")
    md.append("")
    md.append("## サマリ")
    md.append(f"- A: total={a['total']}, unique={a['unique']}, duplicates={a['duplicates']}")
    md.append(f"- B: total={b['total']}, unique={b['unique']}, duplicates={b['duplicates']}")
    md.append(f"- 削減率(count) = {reduction_count:.2%}")
    md.append(f"- 削減率(unique) = {reduction_unique:.2%}")
    md.append(f"- Bのみ新規ユニーク = {len(new_in_b)}")
    return "\n".join(md)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate daily A/B report (JSON + Markdown)")
    ap.add_argument('--in-a', required=True)
    ap.add_argument('--in-b', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--dup-key', default='rule_id,entity_id,time_bucket')
    ap.add_argument('--bucket-minutes', type=int, default=60)
    ap.add_argument('--date-label', default=None)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dup_keys = [x.strip() for x in args.dup_key.split(',') if x.strip()]
    date_label = args.date_label or datetime.date.today().isoformat()

    A = list(load_jsonl(args.in_a))
    B = list(load_jsonl(args.in_b))

    sa = stats(A, dup_keys, args.bucket_minutes)
    sb = stats(B, dup_keys, args.bucket_minutes)

    red_count = (sa["total"] - sb["total"]) / sa["total"] if sa["total"] > 0 else 0.0
    red_unique = (sa["unique"] - sb["unique"]) / sa["unique"] if sa["unique"] > 0 else 0.0

    new_in_b = sb["_uniq_set"] - sa["_uniq_set"]

    result = {
        "date": date_label,
        "dup_key": dup_keys,
        "bucket_minutes": args.bucket_minutes,
        "A": {k: v for k, v in sa.items() if not k.startswith('_')},
        "B": {k: v for k, v in sb.items() if not k.startswith('_')},
        "reduction_by_count": red_count,
        "reduction_by_unique": red_unique,
        "new_in_b": len(new_in_b),
    }
    (out_dir / f"ab_{date_label}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    md = mk_md(date_label, sa, sb, red_count, red_unique, new_in_b)
    (out_dir / f"ab_{date_label}.md").write_text(md, encoding='utf-8')

    print(json.dumps({"ok": True, "out": str(out_dir)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


