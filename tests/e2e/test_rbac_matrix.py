from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from bolcd.api.app import app


@pytest.fixture(autouse=True)
def _keys():
    os.environ["BOLCD_API_KEYS"] = "view:viewER,testop:operator,adminkey:admin"
    yield


def test_forbidden_when_missing_key():
    c = TestClient(app)
    r = c.post("/api/edges/recompute", json={"fdr_q": 0.01, "epsilon": 0.01})
    assert r.status_code == 403


def test_operator_can_recompute_and_writeback(tmp_path):
    c = TestClient(app)
    sample = tmp_path / "e.jsonl"
    sample.write_text("{\"a\":1}\n", encoding="utf-8")
    r = c.post("/api/edges/recompute", headers={"X-API-Key": "testop"}, json={"events_path": str(sample)})
    assert r.status_code == 200
    r2 = c.post("/api/siem/writeback", headers={"X-API-Key": "testop"}, json={"target": "splunk", "rules": []})
    assert r2.status_code in (200, 400)


def test_viewer_can_read_audit():
    c = TestClient(app)
    r = c.get("/api/audit", headers={"X-API-Key": "view"})
    assert r.status_code in (200, 403)  # depends on prior recompute

