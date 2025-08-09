from __future__ import annotations

from bolcd.connectors.normalize import normalize_event_to_logical
from bolcd.connectors.splunk import SplunkConnector
from bolcd.connectors.sentinel import SentinelConnector
from bolcd.connectors.opensearch import OpenSearchConnector


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


ess = [
    (SplunkConnector("http://splunk", "tkn"), []),
    (SentinelConnector("workspace", "tkn"), []),
    (OpenSearchConnector("http://os", {"basic": "x"}), []),
]


def test_connectors_stubs():
    for conn, _ in ess:
        assert conn.writeback([{"name": "rule1"}])["written"] == 1


