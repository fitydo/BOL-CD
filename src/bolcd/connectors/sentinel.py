from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


class SentinelConnector:
    def __init__(self, workspace_id: str, token: str, client: Optional[Any] = None):
        self.workspace_id = workspace_id
        self.token = token
        self.client = client or (httpx and httpx.Client())

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def ingest(self, kql: str) -> Iterable[Dict[str, Any]]:
        url = f"https://api.loganalytics.io/v1/workspaces/{self.workspace_id}/query"
        if not self.client:
            return []
        resp = self.client.post(url, headers=self._auth_headers(), json={"query": kql})
        resp.raise_for_status()
        data = resp.json()
        # Flatten tables (minimal)
        tables = data.get("tables") or []
        out = []
        for t in tables:
            cols = [c["name"] for c in t.get("columns", [])]
            for row in t.get("rows", []):
                out.append({c: v for c, v in zip(cols, row)})
        return out

    def writeback(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Placeholder: actual write-back would use ARM/Management API to create Analytics rules
        return {"status": "skipped", "written": 0}
