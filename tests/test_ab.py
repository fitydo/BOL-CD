from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_ab_report_effects_fields(tmp_path: Path) -> None:
    # Prepare minimal A and B with one overlapping and one B-only (regression)
    a_rows = [
        {"host": "h1", "index": "i", "sourcetype": "st", "source": "s", "component": "c", "group": "g"},
        {"host": "h2", "index": "i", "sourcetype": "st", "source": "s", "component": "c", "group": "g"},
    ]
    b_rows = [
        {"host": "h1", "index": "i", "sourcetype": "st", "source": "s", "component": "c", "group": "g"},
        {"host": "h3", "index": "i", "sourcetype": "st", "source": "s", "component": "c", "group": "g"},  # new in B
    ]

    a_path = tmp_path / "a.jsonl"
    b_path = tmp_path / "b.jsonl"
    out_prefix = tmp_path / "ab_out"
    write_jsonl(a_path, a_rows)
    write_jsonl(b_path, b_rows)

    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parents[1] / "scripts" / "ab_report.py"),
        "--a",
        str(a_path),
        "--b",
        str(b_path),
        "--out-prefix",
        str(out_prefix),
        "--keys",
        "host",
        "index",
        "sourcetype",
        "source",
        "component",
        "group",
    ]
    subprocess.run(cmd, check=True)

    data = json.loads((out_prefix.with_suffix(".json")).read_text(encoding="utf-8"))
    eff = data["effects"]
    assert "reduction_by_count" in eff
    assert "reduction_by_unique" in eff
    assert "suppressed_count" in eff
    assert "suppressed_unique" in eff
    assert eff.get("new_in_b_unique") == 1
    assert eff.get("new_in_b_count") == 1


def test_ab_weekly_md_rows_and_no_data(tmp_path: Path) -> None:
    # Prepare one daily A/B file for today
    today = date.today().isoformat()
    data_raw = tmp_path / "data" / "raw"
    write_jsonl(data_raw / f"splunk_A_{today}.jsonl", [{"x": 1}])
    write_jsonl(data_raw / f"splunk_B_{today}.jsonl", [])

    out_prefix = tmp_path / "reports" / f"ab_weekly_{today}"

    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parents[1] / "scripts" / "ab_weekly.py"),
        "--prefix-a",
        str(data_raw / "splunk_A_"),
        "--prefix-b",
        str(data_raw / "splunk_B_"),
        "--start",
        today,
        "--end",
        today,
        "--out-prefix",
        str(out_prefix),
    ]
    subprocess.run(cmd, check=True)

    md = (out_prefix.with_suffix(".md")).read_text(encoding="utf-8")
    assert today in md
    assert "|date|A|B|" in md

    # No-data range
    nodata_prefix = tmp_path / "reports" / "ab_weekly_nodata"
    cmd2 = [
        sys.executable,
        str(Path(__file__).resolve().parents[1] / "scripts" / "ab_weekly.py"),
        "--prefix-a",
        str(data_raw / "splunk_A_"),
        "--prefix-b",
        str(data_raw / "splunk_B_"),
        "--start",
        "1999-01-01",
        "--end",
        "1999-01-01",
        "--out-prefix",
        str(nodata_prefix),
    ]
    subprocess.run(cmd2, check=True)
    md2 = (nodata_prefix.with_suffix(".md")).read_text(encoding="utf-8")
    assert "> No data" in md2


