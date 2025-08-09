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
        self.client = client or (httpx and httpx.Client(timeout=30.0))

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Splunk {self.token}"}

    def ingest(self, query: str) -> Iterable[Dict[str, Any]]:
        """Run a streaming export search. Yields result dicts.
        Falls back to JSON body list if present.
        """
        url = f"{self.base_url}/services/search/jobs/export"
        data = {"search": f"search {query}", "output_mode": "json"}
        if not self.client:
            return []
        resp = self.client.post(url, headers=self._auth_headers(), data=data)
        resp.raise_for_status()
        # Try streaming lines first
        results: List[Dict[str, Any]] = []
        try:
            for line in resp.text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    import json as _json

                    payload = _json.loads(line)
                    if isinstance(payload, dict) and "result" in payload:
                        results.append(payload["result"])  # type: ignore[index]
                    elif isinstance(payload, dict):
                        results.append(payload)
                except Exception:
                    continue
            if results:
                return results
        except Exception:
            pass
        # Fallback full JSON
        payload = resp.json()
        if isinstance(payload, list):
            return payload
        return payload.get("results", [])

    def writeback(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create/update saved searches with provided SPL; idempotent on name.
        This is a minimal placeholder; many deployments will need app/owner scoping.
        """
        written = 0
        if not self.client:
            return {"status": "skipped", "written": 0}
        for rule in rules:
            name = rule.get("name", "bolcd_rule")
            spl = rule.get("spl") or rule.get("query") or rule.get("search") or "index=main | head 1"
            # Check existence
            get_url = f"{self.base_url}/servicesNS/nobody/search/saved/searches/{name}"
            r = self.client.get(get_url, headers=self._auth_headers())
            # Create or update
            if r.status_code == 404:
                post_url = f"{self.base_url}/servicesNS/nobody/search/saved/searches"
                data = {"name": name, "search": spl}
                rr = self.client.post(post_url, headers=self._auth_headers(), data=data)
                rr.raise_for_status()
            else:
                update_url = get_url
                data = {"search": spl}
                rr = self.client.post(update_url, headers=self._auth_headers(), data=data)
                rr.raise_for_status()
            written += 1
        return {"status": "ok", "written": written}
