from __future__ import annotations

from typing import Any, Dict, Iterable, List


class SplunkConnector:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def ingest(self, query: str) -> Iterable[Dict[str, Any]]:
        # Stub: return empty iterable; real impl would call Splunk REST
        return []

    def writeback(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Stub: simulate success
        return {"status": "ok", "written": len(rules)}
