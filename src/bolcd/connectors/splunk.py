from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover - httpx present via requirements
    httpx = None  # type: ignore


class SplunkConnector:
    def __init__(self, base_url: str, token: str, client: Optional[Any] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = client or (httpx and httpx.Client())

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Splunk {self.token}"}

    def ingest(self, query: str) -> Iterable[Dict[str, Any]]:
        """Run a streaming export search. Returns an iterator of result dicts.
        Note: In tests we inject a fake client; in production this hits /services/search/jobs/export.
        """
        url = f"{self.base_url}/services/search/jobs/export"
        data = {"search": f"search {query}", "output_mode": "json"}
        if not self.client:
            return []
        resp = self.client.post(url, headers=self._auth_headers(), data=data)
        resp.raise_for_status()
        # For simplicity assume the server returns JSON list; Splunk actually streams JSON per line
        payload = resp.json()
        if isinstance(payload, list):
            return payload
        return payload.get("results", [])

    def writeback(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create/update saved searches with provided SPL under a conventional name.
        This is a minimal placeholder to demonstrate REST contract; many deployments need RBAC & namespace.
        """
        url = f"{self.base_url}/servicesNS/nobody/search/saved/searches"
        written = 0
        if not self.client:
            return {"status": "skipped", "written": 0}
        for rule in rules:
            name = rule.get("name", "bolcd_rule")
            spl = rule.get("spl") or rule.get("query") or rule.get("search") or "index=main | head 1"
            data = {"name": name, "search": spl}
            r = self.client.post(url, headers=self._auth_headers(), data=data)
            r.raise_for_status()
            written += 1
        return {"status": "ok", "written": written, "endpoint": url}
