import json
import pathlib
import subprocess
import sys
import datetime


def write_jsonl(p, rows):
    with open(p, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


def test_ab_pipeline(tmp_path: pathlib.Path):
    events = []
    base = datetime.datetime(2025, 1, 1, 10, 0, 0)
    for i in range(200):
        events.append({
            "ts": (base + datetime.timedelta(minutes=i % 60)).isoformat(),
            "entity_id": f"host-{i % 10}",
            "rule_id": f"R-{i % 3}",
        })
    inp = tmp_path / 'events.jsonl'
    write_jsonl(inp, events)

    out = tmp_path / 'ab'
    out.mkdir()
    subprocess.check_call([sys.executable, 'scripts/ab/ab_split.py', '--in', str(inp), '--out-dir', str(out)])

    rep = tmp_path / 'reports'
    rep.mkdir()
    subprocess.check_call([sys.executable, 'scripts/ab/ab_report.py', '--in-a', str(out / 'A.jsonl'), '--in-b', str(out / 'B.jsonl'), '--out-dir', str(rep), '--date-label', '2099-01-01'])
    j = json.loads((rep / 'ab_2099-01-01.json').read_text(encoding='utf-8'))
    assert 'reduction_by_count' in j and 'reduction_by_unique' in j

    subprocess.check_call([sys.executable, 'scripts/ab/ab_weekly.py', '--dir', str(rep), '--out', str(rep / 'weekly.json')])
    w = json.loads((rep / 'weekly.json').read_text(encoding='utf-8'))
    assert 'reduction_by_count' in w


