from __future__ import annotations

from bolcd.connectors.opensearch import OpenSearchConnector


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


def test_opensearch_ingest_hits():
    payload = {"hits": {"hits": [{"_source": {"x": 1}}, {"_source": {"x": 2}}]}}
    conn = OpenSearchConnector("http://os", {"basic": "abc"}, client=MockClient(posts=[MockResp(json_obj=payload)]))
    out = list(conn.ingest({"query": {"match_all": {}}}))
    assert [r["x"] for r in out] == [1, 2]


def test_opensearch_writeback_puts():
    conn = OpenSearchConnector("http://os", {"basic": "abc"}, client=MockClient(puts=[MockResp(), MockResp()]))
    res = conn.writeback([{"name": "r1"}, {"name": "r2"}])
    assert res["written"] == 2

