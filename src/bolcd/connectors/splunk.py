from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover - httpx present via requirements
    httpx = None  # type: ignore


class SplunkConnector:
    def __init__(self, base_url: str, token: str, client: Optional[Any] = None, timeout: float = 30.0, retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.retries = retries
        self.client = client or (httpx and httpx.Client(timeout=timeout))

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Splunk {self.token}"}

    def _post(self, url: str, **kwargs) -> Any:
        last_exc: Exception | None = None
        for _ in range(self.retries + 1):
            try:
                r = self.client.post(url, **kwargs)  # type: ignore[union-attr]
                r.raise_for_status()
                return r
            except Exception as e:  # pragma: no cover
                last_exc = e
        if last_exc:
            raise last_exc

    def _get(self, url: str, **kwargs) -> Any:
        last_exc: Exception | None = None
        for _ in range(self.retries + 1):
            try:
                # Do not raise on 404; caller uses status_code to branch
                r = self.client.get(url, **kwargs)  # type: ignore[union-attr]
                return r
            except Exception as e:  # pragma: no cover
                last_exc = e
        if last_exc:
            raise last_exc

    def ingest(self, query: str) -> Iterable[Dict[str, Any]]:
        """Run a streaming export search. Yields result dicts.
        Falls back to JSON body list if present.
        """
        url = f"{self.base_url}/services/search/jobs/export"
        data = {"search": f"search {query}", "output_mode": "json"}
        if not self.client:
            return []
        resp = self._post(url, headers=self._auth_headers(), data=data)
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
        # Fallback full JSON with basic pagination support
        payload = resp.json()
        if isinstance(payload, list):
            return payload
        out = payload.get("results", [])
        if payload.get("next_offset") is not None:
            offset = payload["next_offset"]
            while offset is not None:
                more = self._post(url, headers=self._auth_headers(), data={**data, "offset": offset}).json()
                out.extend(more.get("results", []))
                offset = more.get("next_offset")
        return out

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
            try:
                r = self._get(get_url, headers=self._auth_headers())
                exists = r.status_code == 200
            except Exception:
                exists = False
            # Create or update
            if not exists:
                post_url = f"{self.base_url}/servicesNS/nobody/search/saved/searches"
                data = {"name": name, "search": spl}
                rr = self._post(post_url, headers=self._auth_headers(), data=data)
                rr.raise_for_status()
            else:
                update_url = get_url
                data = {"search": spl}
                rr = self._post(update_url, headers=self._auth_headers(), data=data)
                rr.raise_for_status()
            written += 1
        return {"status": "ok", "written": written}
