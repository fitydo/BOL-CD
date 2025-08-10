from __future__ import annotations

from bolcd.connectors.sentinel import SentinelConnector


class MockResp:
    def __init__(self, json_obj=None, status_code: int = 200):
        self._json = json_obj or {}
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


class MockClient:
    def __init__(self, posts=None, puts=None):
        self.posts = posts or []
        self.puts = puts or []

    def post(self, url, **kwargs):
        return self.posts.pop(0)

    def put(self, url, **kwargs):
        return self.puts.pop(0)


def test_sentinel_ingest_parses_tables():
    payload = {"tables": [{"columns": [{"name": "a"}], "rows": [[1], [2]]}]}
    c = SentinelConnector("ws", "tkn", client=MockClient(posts=[MockResp(json_obj=payload)]))
    out = list(c.ingest("KQL"))
    assert [r["a"] for r in out] == [1, 2]


def test_sentinel_writeback_put():
    c = SentinelConnector("ws", "tkn", client=MockClient(puts=[MockResp(), MockResp()]), subscription_id="s", resource_group="rg", workspace_name="wsname")
    res = c.writeback([{"name": "r1", "kql": "SecurityEvent | take 1"}, {"name": "r2", "kql": "SecurityEvent | take 1"}])
    assert res["written"] == 2

