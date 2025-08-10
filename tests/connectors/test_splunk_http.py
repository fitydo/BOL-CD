from __future__ import annotations

import json
from types import SimpleNamespace

from bolcd.connectors.splunk import SplunkConnector


class MockResp:
    def __init__(self, text: str = "", json_obj=None, status_code: int = 200, next_offset=None):
        self._text = text
        self._json = json_obj
        self.status_code = status_code
        self.next_offset = next_offset

    @property
    def text(self):
        return self._text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


class MockClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)


def test_splunk_ingest_streaming_and_pagination():
    # First call returns JSON results with next_offset; second provides more results
    first = MockResp(json_obj={"results": [{"a": 1}], "next_offset": 10})
    second = MockResp(json_obj={"results": [{"a": 2}], "next_offset": None})
    client = MockClient([first, second])
    c = SplunkConnector("http://splunk", "tkn", client=client)
    out = list(c.ingest("index=main | head 2"))
    assert [r["a"] for r in out] == [1, 2]


def test_splunk_writeback_upsert():
    # Existence -> 404 then create, then update existing
    not_found = MockResp(status_code=404)  # GET exists -> 404
    created = MockResp(json_obj={})       # POST create -> 200
    exists = MockResp(status_code=200)    # GET exists -> 200
    updated = MockResp(json_obj={})       # POST update -> 200
    client = MockClient([not_found, created, exists, updated])
    c = SplunkConnector("http://splunk", "tkn", client=client)
    res = c.writeback([
        {"name": "r1", "spl": "index=main | head 1"},
        {"name": "r1", "spl": "index=main | head 1"},
    ])
    assert res["written"] == 2

