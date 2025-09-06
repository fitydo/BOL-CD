#!/usr/bin/env python3
# scripts/kpi/compute_kpi.py
import argparse
import json
import pathlib
import datetime
import statistics
from dateutil import parser as dtp


def load_jsonl(p):
    path = pathlib.Path(p)
    if not path.exists():
        return []
    with path.open(encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def load_json(p):
    path = pathlib.Path(p)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def iso2dt(s):
    if not s:
        return None
    try:
        return dtp.parse(s)
    except Exception:
        return None


def seconds(a, b):
    if not a or not b:
        return None
    return max(0.0, (b - a).total_seconds())


def median_safe(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return statistics.median(xs)


def pctl(xs, q):
    xs = sorted([x for x in xs if x is not None])
    if not xs:
        return None
    idx = int(round((len(xs) - 1) * q))
    return xs[idx]


def main():
    ap = argparse.ArgumentParser(description="Compute daily KPI from AB reports and cases")
    ap.add_argument('--date', default=None, help='YYYY-MM-DD. Default: UTC today')
    ap.add_argument('--reports-dir', default='/reports')
    ap.add_argument('--cases', default=None, help='cases jsonl path (optional)')
    ap.add_argument('--ab-json', default=None, help='ab_YYYY-MM-DD.json full path override')
    ap.add_argument('--ingest-a-gb', type=float, default=None, help='A ingest GB (optional)')
    ap.add_argument('--ingest-b-gb', type=float, default=None, help='B ingest GB (optional)')
    ap.add_argument('--cost-per-gb-usd', type=float, default=None, help='SIEM $/GB (optional)')
    ap.add_argument('--out', default=None, help='output path. Default: /reports/kpi_YYYY-MM-DD.json')
    args = ap.parse_args()

    today = args.date or datetime.date.today().isoformat()
    reports = pathlib.Path(args.reports_dir)
    reports.mkdir(parents=True, exist_ok=True)

    # --- Noise: ab daily JSON ---
    ab_path = pathlib.Path(args.ab_json) if args.ab_json else (reports / f"ab_{today}.json")
    ab = load_json(ab_path) or {}
    noise = {
        "A_total": ab.get("A", {}).get("total"),
        "A_unique": ab.get("A", {}).get("unique"),
        "A_duplicates": ab.get("A", {}).get("duplicates"),
        "B_total": ab.get("B", {}).get("total"),
        "B_unique": ab.get("B", {}).get("unique"),
        "B_duplicates": ab.get("B", {}).get("duplicates"),
        "reduction_by_count": ab.get("reduction_by_count"),
        "reduction_by_unique": ab.get("reduction_by_unique"),
        "new_in_b": ab.get("new_in_b"),
    }

    # --- Ops efficiency + Risk: cases analysis ---
    triage_seconds = []
    mttd_seconds = []
    mttr_seconds = []
    backlog_untriaged = None
    backlog_ratio = None
    cases_total = None

    if args.cases:
        cases = list(load_jsonl(args.cases))
        cases_total = len(cases)
        opened = 0
        untriaged = 0
        for c in cases:
            det = iso2dt(c.get("detected_at") or c.get("opened_at"))
            tri = iso2dt(c.get("triaged_at") or c.get("triage_started_at"))
            res = iso2dt(c.get("resolved_at") or c.get("closed_at"))

            if det:
                opened += 1
            if tri and res:
                triage_seconds.append(seconds(tri, res))

            # Risk: MTTD/MTTR
            if det and tri:
                mttd_seconds.append(seconds(det, tri))
            if det and res:
                mttr_seconds.append(seconds(det, res))

            status = (c.get("status") or "").lower()
            if status in ("open", "new", "investigating", "") or (det and not res):
                untriaged += 1

        backlog_untriaged = untriaged
        backlog_ratio = (untriaged / opened) if opened else None

    ops = {
        "triage_p50_seconds": median_safe(triage_seconds),
        "triage_p90_seconds": pctl(triage_seconds, 0.90),
        "cases_processed_daily": cases_total,
    }
    risk = {
        "backlog_untriaged": backlog_untriaged,
        "backlog_ratio": backlog_ratio,
        "mttd_median_seconds": median_safe(mttd_seconds),
        "mttr_median_seconds": median_safe(mttr_seconds),
    }

    # --- Cost: A/B ingest + $/GB ---
    cost = {}
    if args.ingest_a_gb is not None and args.ingest_b_gb is not None:
        cost["ingest_gb_A"] = args.ingest_a_gb
        cost["ingest_gb_B"] = args.ingest_b_gb
        if args.cost_per_gb_usd is not None:
            saved_gb = max(0.0, args.ingest_a_gb - args.ingest_b_gb)
            cost["cost_per_gb_usd"] = args.cost_per_gb_usd
            cost["savings_usd"] = saved_gb * args.cost_per_gb_usd

    out = {
        "date": today,
        "noise": noise,
        "ops": ops,
        "risk": risk,
        "cost": cost
    }
    out_path = pathlib.Path(args.out) if args.out else (reports / f"kpi_{today}.json")
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

