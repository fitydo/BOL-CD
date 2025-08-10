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
        self.client = client or (httpx and httpx.Client(timeout=30.0))

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if "basic" in self.auth:
            headers["Authorization"] = f"Basic {self.auth['basic']}"
        return headers

    def ingest(self, dsl: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        url = f"{self.endpoint}/_search"
        if not self.client:
            return []
        # Retry once on failure
        last: Exception | None = None
        for _ in range(3):
            try:
                resp = self.client.post(url, json=dsl, headers=self._headers())
                resp.raise_for_status()
                break
            except Exception as e:  # pragma: no cover
                last = e
        else:
            if last:
                raise last
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        return [h.get("_source", {}) for h in hits]

    def _validate_rule(self, rule: Dict[str, Any]) -> None:
        # Minimal validation
        if not rule.get("name"):
            raise ValueError("rule missing name")

    def writeback(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Index rules into bolcd-rules index (idempotent by name). Optionally create detector stub."""
        if not self.client:
            return {"status": "skipped", "written": 0}
        written = 0
        for rule in rules:
            self._validate_rule(rule)
            name = rule.get("name")
            url = f"{self.endpoint}/bolcd-rules/_doc/{name}"
            # Idempotent upsert
            last: Exception | None = None
            for _ in range(3):
                try:
                    r = self.client.put(url, json=rule, headers=self._headers())
                    r.raise_for_status()
                    break
                except Exception as e:  # pragma: no cover
                    last = e
            else:
                if last:
                    raise last
            written += 1
        return {"status": "ok", "written": written}
