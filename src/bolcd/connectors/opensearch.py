from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


class OpenSearchConnector:
    def __init__(self, endpoint: str, auth: Dict[str, str], client: Optional[Any] = None):
        self.endpoint = endpoint.rstrip("/")
        self.auth = auth
        self.client = client or (httpx and httpx.Client())

    def ingest(self, dsl: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        url = f"{self.endpoint}/_search"
        if not self.client:
            return []
        headers = {}
        if "basic" in self.auth:
            headers["Authorization"] = f"Basic {self.auth['basic']}"
        resp = self.client.post(url, json=dsl, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        return [h.get("_source", {}) for h in hits]

    def writeback(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Placeholder: Typically create detector findings or index a policy doc
        return {"status": "skipped", "written": 0}
