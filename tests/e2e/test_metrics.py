from __future__ import annotations

from fastapi.testclient import TestClient

from bolcd.api.app import app


def test_metrics_endpoint():
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    assert b"bolcd_requests_total" in r.content

