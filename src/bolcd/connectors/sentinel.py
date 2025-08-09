from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


class SentinelConnector:
    def __init__(
        self,
        workspace_id: str,
        token: str,
        client: Optional[Any] = None,
        subscription_id: str | None = None,
        resource_group: str | None = None,
        workspace_name: str | None = None,
    ):
        self.workspace_id = workspace_id
        self.token = token
        self.client = client or (httpx and httpx.Client(timeout=30.0))
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.workspace_name = workspace_name

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def ingest(self, kql: str) -> Iterable[Dict[str, Any]]:
        url = f"https://api.loganalytics.io/v1/workspaces/{self.workspace_id}/query"
        if not self.client:
            return []
        resp = self.client.post(url, headers=self._auth_headers(), json={"query": kql})
        resp.raise_for_status()
        data = resp.json()
        tables = data.get("tables") or []
        out = []
        for t in tables:
            cols = [c["name"] for c in t.get("columns", [])]
            for row in t.get("rows", []):
                out.append({c: v for c, v in zip(cols, row)})
        return out

    def writeback(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create/Update Scheduled Analytics Rules via ARM API (idempotent).
        Requires subscription_id, resource_group, workspace_name.
        """
        if not (self.client and self.subscription_id and self.resource_group and self.workspace_name):
            return {"status": "skipped", "written": 0, "reason": "missing ARM config"}
        api_version = "2023-02-01-preview"
        base = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.OperationalInsights/workspaces/{self.workspace_name}/providers/"
            f"Microsoft.SecurityInsights/alertRules"
        )
        written = 0
        for rule in rules:
            name = rule.get("name", "bolcd_rule")
            kql = rule.get("kql") or rule.get("query") or rule.get("search") or "SecurityEvent | take 1"
            frequency = rule.get("queryFrequency", "PT5M")
            period = rule.get("queryPeriod", "PT5M")
            severity = rule.get("severity", "Medium")
            body = {
                "kind": "Scheduled",
                "properties": {
                    "displayName": name,
                    "enabled": True,
                    "query": kql,
                    "queryFrequency": frequency,
                    "queryPeriod": period,
                    "severity": severity,
                    "triggerOperator": "GreaterThan",
                    "triggerThreshold": 0,
                },
            }
            get_url = f"{base}/{name}?api-version={api_version}"
            # PUT is both create or replace; existence check only for idempotency semantics/logging
            put_url = get_url
            rr = self.client.put(put_url, headers=self._auth_headers(), json=body)
            rr.raise_for_status()
            written += 1
        return {"status": "ok", "written": written}
