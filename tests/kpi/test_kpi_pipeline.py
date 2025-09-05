import json
import pathlib
import subprocess
import sys
import datetime


def write_json(p, obj):
    pathlib.Path(p).write_text(json.dumps(obj), encoding='utf-8')


def write_jsonl(p, rows):
    with open(p, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


def test_kpi_e2e(tmp_path: pathlib.Path):
    reports = tmp_path / 'reports'
    reports.mkdir()
    today = '2099-01-01'
    
    # ab JSON (daily)
    write_json(reports / f"ab_{today}.json", {
        "A": {"total": 1000, "unique": 400, "duplicates": 600},
        "B": {"total": 700, "unique": 350, "duplicates": 350},
        "reduction_by_count": 0.3,
        "reduction_by_unique": 0.125,
        "new_in_b": 5
    })
    
    # cases (simple)
    base = datetime.datetime(2099, 1, 1, 0, 0, 0)
    rows = []
    for i in range(50):
        det = base + datetime.timedelta(minutes=i)
        tri = det + datetime.timedelta(minutes=5)
        res = tri + datetime.timedelta(minutes=10)
        rows.append({
            "case_id": f"C{i}",
            "detected_at": det.isoformat(),
            "triaged_at": tri.isoformat(),
            "resolved_at": res.isoformat(),
            "status": "closed"
        })
    write_jsonl(tmp_path / 'cases.jsonl', rows)

    # KPI computation
    subprocess.check_call([
        sys.executable, 'scripts/kpi/compute_kpi.py',
        '--date', today,
        '--reports-dir', str(reports),
        '--cases', str(tmp_path / 'cases.jsonl'),
        '--ingest-a-gb', '200', '--ingest-b-gb', '160', '--cost-per-gb-usd', '4.3'
    ])

    # KPI JSON generated
    out = json.loads((reports / f'kpi_{today}.json').read_text(encoding='utf-8'))
    assert out['noise']['reduction_by_count'] == 0.3
    assert out['ops']['triage_p50_seconds'] is not None
    assert out['risk']['mttd_median_seconds'] is not None
    assert out['cost']['savings_usd'] == 40 * 4.3  # (200-160) * 4.3
