from __future__ import annotations

from bolcd.connectors.normalize import normalize_to_ocsf
from bolcd.connectors.sigma import SplunkConnector, SentinelConnector, OpenSearchConnector, parse_sigma_to_events


def test_normalize_to_ocsf_basic_mapping():
    ev = {"host_name": "h", "user_name": "u", "process_name": "p", "asset": {"tier": "gold"}}
    out = normalize_to_ocsf(ev)
    assert out["host"] == "h"
    assert out["user"] == "u"
    assert out["process"] == "p"
    assert out["asset.tier"] == "gold"


def test_sigma_parse_minimal():
    rule = {
        "detection": {
            "selection1": {"fieldA": "x"},
            "condition": "selection1",
        }
    }
    sr = parse_sigma_to_events(rule)
    assert sr.condition == "selection1"
    assert "fieldA" in sr.fields


def test_connectors_writeback_stub():
    rules = [{"name": "r1"}, {"name": "r2"}]
    assert SplunkConnector("http://splunk", "t").write_back_rules(rules)["count"] == 2
    assert SentinelConnector("ws", object()).write_back_rules(rules)["count"] == 2
    assert OpenSearchConnector("https://os", ("u", "p")).write_back_rules(rules)["count"] == 2


