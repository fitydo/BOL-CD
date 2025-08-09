from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bolcd.api.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_encode(client: TestClient):
    body = {"events": [{"x": 0.0}, {"x": 1.0}], "thresholds": {"x": 0.5}, "margin_delta": 0.0}
    r = client.post("/api/encode", json=body)
    assert r.status_code == 200
    assert "vectors" in r.json()


def test_recompute_and_graph(client: TestClient, tmp_path):
    # Use sample events file path
    sample = tmp_path / "sample.jsonl"
    sample.write_text("{\"ps_exec_count\":2, \"network_beacon_score\":0.9}\n", encoding="utf-8")
    r = client.post(
        "/api/edges/recompute",
        json={"events_path": str(sample), "epsilon": 0.02, "fdr_q": 0.01, "persist_dir": str(tmp_path)},
    )
    assert r.status_code == 200
    g = client.get("/api/graph").json()
    assert "nodes" in g and "edges" in g
    # graphml
    r2 = client.get("/api/graph", params={"format": "graphml"})
    assert r2.status_code == 200 and "<graphml" in r2.text


def test_writeback_dry_run(client: TestClient):
    r = client.post(
        "/api/siem/writeback",
        json={"target": "splunk", "rules": [{"name": "r1", "spl": "index=main | head 1"}]},
    )
    assert r.status_code == 200 and r.json()["status"] in ("dry-run", "ok")
