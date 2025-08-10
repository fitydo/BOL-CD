from __future__ import annotations

from bolcd.connectors.normalize import normalize_event_to_logical
from bolcd.connectors.splunk import SplunkConnector
from bolcd.connectors.sentinel import SentinelConnector
from bolcd.connectors.opensearch import OpenSearchConnector
from bolcd.connectors.sigma import load_sigma_yaml, parse_sigma_to_events


def test_normalize_event_to_logical():
    ev = {
        "@timestamp": "2025-01-01T00:00:00Z",
        "source.ip": "10.0.0.1",
        "destination.ip": "10.0.0.2",
        "user.name": "alice",
        "process.name": "powershell.exe",
        "event.action": "dns_query",
        "threat.technique.id": "T1059",
    }
    out = normalize_event_to_logical(ev)
    assert out["src_ip"] == "10.0.0.1"
    assert out["dst_ip"] == "10.0.0.2"
    assert out["user"] == "alice"
    assert out["process"] == "powershell.exe"
    assert out["action"] == "dns_query"
    assert out["technique"] == "T1059"


class FakeResp:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")
        return None

    def json(self):
        return self._payload

    @property
    def text(self):
        import json as _json

        if isinstance(self._payload, (dict, list)):
            return "\n".join([_json.dumps(self._payload)])
        return str(self._payload)


class FakeClient:
    def __init__(self, payload):
        self.payload = payload

    def post(self, *args, **kwargs):  # noqa: D401 - test stub
        return FakeResp(self.payload)

    def get(self, *args, **kwargs):  # noqa: D401 - test stub
        # simulate 404 for existence check
        return FakeResp({}, status_code=404)

    def put(self, *args, **kwargs):  # noqa: D401 - test stub
        return FakeResp({})


def test_connectors_ingest_and_writeback_stubs():
    # Splunk ingest expects list or {results: []}
    splunk = SplunkConnector("http://splunk", "tkn", client=FakeClient(payload=[{"a": 1}]))
    assert list(splunk.ingest("index=main")) == [{"a": 1}]
    assert splunk.writeback([{"name": "r1", "spl": "index=main | head 1"}])["written"] == 1

    # Sentinel flatten tables
    sentinel_payload = {"tables": [{"columns": [{"name": "a"}], "rows": [[1], [2]]}]}
    sentinel = SentinelConnector("ws", "tkn", client=FakeClient(payload=sentinel_payload))
    assert [r["a"] for r in sentinel.ingest("KQL") ] == [1, 2]

    # OpenSearch returns _source list
    os_payload = {"hits": {"hits": [{"_source": {"x": 1}}, {"_source": {"x": 2}}]}}
    os_conn = OpenSearchConnector("http://os", {"basic": "abc"}, client=FakeClient(payload=os_payload))
    assert [r["x"] for r in os_conn.ingest({"query": {"match_all": {}}})] == [1, 2]

def test_sigma_parse(tmp_path):
    y = tmp_path / "r.yml"
    y.write_text(
        """
title: Example
detection:
  sel:
    ps_exec_count: 1
  condition: sel
timeframe: 5m
        """,
        encoding="utf-8",
    )
    data = load_sigma_yaml(str(y))
    sr = parse_sigma_to_events(data)
    assert "ps_exec_count" in sr.fields
    assert sr.condition == "sel"
