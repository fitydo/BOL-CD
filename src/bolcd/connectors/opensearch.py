from __future__ import annotations

from typing import Any, Dict, Iterable, List


class OpenSearchConnector:
    def __init__(self, endpoint: str, auth: Dict[str, str]):
        self.endpoint = endpoint.rstrip("/")
        self.auth = auth

    def ingest(self, dsl: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        return []

    def writeback(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"status": "ok", "written": len(rules)}
