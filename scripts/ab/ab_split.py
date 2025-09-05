#!/usr/bin/env python3
import argparse
import json
import hashlib
import sys
import pathlib


def assign_arm(stable_key: str, salt: str) -> str:
    h = hashlib.sha256((salt + '|' + stable_key).encode('utf-8')).hexdigest()
    return 'A' if int(h, 16) % 2 == 0 else 'B'


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic A/B assignment")
    ap.add_argument('--in', dest='inp', required=True, help='input JSONL path')
    ap.add_argument('--out-dir', required=True, help='output dir; creates A.jsonl/B.jsonl with arm field')
    ap.add_argument('--key-fields', default='entity_id,rule_id',
                    help='comma-separated fields used for deterministic assignment')
    ap.add_argument('--salt', default='BOLCD_AB_v1', help='salt string for hashing')
    args = ap.parse_args()

    in_path = pathlib.Path(args.inp)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    a_path = out_dir / 'A.jsonl'
    b_path = out_dir / 'B.jsonl'

    key_fields = [f.strip() for f in args.key_fields.split(',') if f.strip()]

    cnt = {'A': 0, 'B': 0}
    with in_path.open(encoding='utf-8') as f, a_path.open('w', encoding='utf-8') as fa, b_path.open('w', encoding='utf-8') as fb:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            try:
                stable_key = '|'.join(str(rec.get(k, '')) for k in key_fields)
            except Exception:
                stable_key = str(rec.get('entity_id', ''))
            arm = assign_arm(stable_key, args.salt)
            rec['arm'] = arm
            out = fa if arm == 'A' else fb
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            cnt[arm] += 1

    print(json.dumps({"assigned": cnt}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())


