from __future__ import annotations

import os
from typing import Any, Mapping

from .splunk import SplunkConnector
from .sentinel import SentinelConnector
from .opensearch import OpenSearchConnector


def make_connector(target: str, env: Mapping[str, str] | None = None, client: Any | None = None):
    env = env or os.environ
    t = target.lower()
    if t == "splunk":
        base_url = env.get("BOLCD_SPLUNK_URL", "http://localhost:8089")
        token = env.get("BOLCD_SPLUNK_TOKEN", "")
        return SplunkConnector(base_url, token, client=client)
    if t == "sentinel":
        ws = env.get("BOLCD_SENTINEL_WORKSPACE_ID", "")
        token = env.get("BOLCD_AZURE_TOKEN", "")
        return SentinelConnector(ws, token, client=client)
    if t == "opensearch":
        endpoint = env.get("BOLCD_OPENSEARCH_ENDPOINT", "http://localhost:9200")
        basic = env.get("BOLCD_OPENSEARCH_BASIC", "")
        return OpenSearchConnector(endpoint, {"basic": basic} if basic else {}, client=client)
    raise ValueError(f"Unknown target: {target}")
