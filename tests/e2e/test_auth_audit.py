from __future__ import annotations

from fastapi.testclient import TestClient

from bolcd.api.app import app


def test_forbidden_without_key():
    client = TestClient(app)
    r = client.post(
        "/api/edges/recompute",
        json={"fdr_q": 0.05, "epsilon": 0.01, "segment_by": []},
    )
    assert r.status_code == 403


def test_audit_persisted(tmp_path):
    # Set API key mapping in env via client.headers per request
    client = TestClient(app)
    # Allow any key by leaving env empty -> middleware treats as open, but we still set header as actor
    r = client.post(
        "/api/edges/recompute",
        headers={"X-API-Key": "testop"},
        json={"fdr_q": 0.05, "epsilon": 0.02, "segment_by": []},
    )
    assert r.status_code == 200
    r2 = client.get("/api/audit", headers={"X-API-Key": "testviewer"})
    assert r2.status_code == 200
    items = r2.json()
    assert isinstance(items, list)
    # Last entry should be recompute with diff edges/nodes
    assert any(it.get("action") == "recompute" for it in items)

