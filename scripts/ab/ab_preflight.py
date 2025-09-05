#!/usr/bin/env python3
import argparse
import json
import pathlib
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="AB preflight checks")
    ap.add_argument('--reports-dir', required=True, help='Shared reports dir (PVC) mounted by API and Cron')
    ap.add_argument('--expect-balance', type=float, default=0.05, help='Allowed pre A/B count diff ratio')
    ap.add_argument('--preA')
    ap.add_argument('--preB')
    args = ap.parse_args()

    rep = pathlib.Path(args.reports_dir)
    errs = []
    if not rep.exists():
        errs.append(f"reports-dir missing: {rep}")
    if args.preA and args.preB:
        try:
            ca = sum(1 for _ in open(args.preA, encoding='utf-8'))
            cb = sum(1 for _ in open(args.preB, encoding='utf-8'))
            if ca == 0 or cb == 0:
                errs.append("pre-sample count is 0")
            else:
                diff = abs(ca - cb) / max(ca, cb)
                if diff > args.expect_balance:
                    errs.append(f"A/B pre-count diff too large: {diff:.2%} > {args.expect_balance:.2%}")
        except Exception as e:
            errs.append(f"pre-sample read error: {e}")

    if errs:
        print(json.dumps({"ok": False, "errors": errs}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": True}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


