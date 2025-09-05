from pathlib import Path
import json
import importlib

from prometheus_client import CONTENT_TYPE_LATEST  # noqa: F401 (import ensures client available)


def read_metric_value(text: str, name: str) -> float:
    for line in text.splitlines():
        if line.startswith(name + " "):
            return float(line.split(" ", 1)[1])
    raise AssertionError(f"metric {name} not found in exposition")


def test_update_metrics_from_effects_only_json(tmp_path: Path):
    # Lazy import to access module-level globals
    app_mod = importlib.import_module("bolcd.api.app")
    # Point to temp reports dir
    app_mod.BOLCD_REPORTS_DIR = tmp_path

    # Write effects-only JSON (as produced by tee)
    effects = {
        "reduction_by_count": 0.2,
        "reduction_by_unique": 0.15,
        "suppressed_count": 123,
        "new_in_b_unique": 2,
        "new_in_b_count": 5,
    }
    p = tmp_path / "ab_2025-08-11_effects.json"
    p.write_text(json.dumps(effects), encoding="utf-8")

    # Update metrics and export
    app_mod._update_ab_metrics_from_reports()
    text = app_mod.generate_latest(app_mod.REGISTRY).decode("utf-8")

    assert read_metric_value(text, "bolcd_ab_reduction_by_count") == 0.2
    assert read_metric_value(text, "bolcd_ab_reduction_by_unique") == 0.15
    assert read_metric_value(text, "bolcd_ab_suppressed_count") == 123.0
    assert read_metric_value(text, "bolcd_ab_new_in_b_unique") == 2.0
    assert read_metric_value(text, "bolcd_ab_new_in_b_count") == 5.0


def test_update_metrics_from_full_report_json(tmp_path: Path):
    app_mod = importlib.import_module("bolcd.api.app")
    app_mod.BOLCD_REPORTS_DIR = tmp_path

    data = {
        "effects": {
            "reduction_by_count": 0.3,
            "reduction_by_unique": 0.25,
            "suppressed_count": 200,
            # omit new_in_b_* to force fallback from top.new_in_b
        },
        "top": {
            "new_in_b": [
                {"signature": "X", "count": 4},
                {"signature": "Y", "count": 6},
            ]
        },
    }
    p = tmp_path / "ab_2025-08-12.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    app_mod._update_ab_metrics_from_reports()
    text = app_mod.generate_latest(app_mod.REGISTRY).decode("utf-8")

    assert read_metric_value(text, "bolcd_ab_reduction_by_count") == 0.3
    assert read_metric_value(text, "bolcd_ab_reduction_by_unique") == 0.25
    assert read_metric_value(text, "bolcd_ab_suppressed_count") == 200.0
    # Fallback path counts unique and total from top.new_in_b
    assert read_metric_value(text, "bolcd_ab_new_in_b_unique") == 2.0
    assert read_metric_value(text, "bolcd_ab_new_in_b_count") == 10.0


