from __future__ import annotations

from typing import Any, Dict, Iterable, List


class SentinelConnector:
    def __init__(self, workspace_id: str, token: str):
        self.workspace_id = workspace_id
        self.token = token

    def ingest(self, kql: str) -> Iterable[Dict[str, Any]]:
        return []

    def writeback(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"status": "ok", "written": len(rules)}
