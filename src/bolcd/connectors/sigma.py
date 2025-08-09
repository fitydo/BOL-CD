from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class SigmaRule:
    condition: str
    fields: List[str]
    timeframe: str | None = None


def parse_sigma_to_events(rule: Dict[str, Any]) -> SigmaRule:
    """
    Minimal Sigma parser stub sufficient for connector interface.
    Pulls detection.condition, collects referenced fields, timeframe.
    """
    detection = rule.get("detection", {})
    condition = rule.get("condition") or detection.get("condition", "")
    # Collect field matchers like selection1: { field: value }
    fields: List[str] = []
    for k, v in detection.items():
        if k == "condition":
            continue
        if isinstance(v, dict):
            fields.extend(list(v.keys()))
    if not fields:
        fields = sorted(set(rule.get("fields", [])))
    timeframe = rule.get("timeframe") or detection.get("timeframe")
    return SigmaRule(condition=condition, fields=sorted(set(fields)), timeframe=timeframe)


# Placeholder connectors; real implementations require vendor SDKs and auth.
class SplunkConnector:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def write_back_rules(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Convert rules to SPL or savedsearches; here we just echo for demo
        return {"status": "ok", "count": len(rules)}


class SentinelConnector:
    def __init__(self, workspace_id: str, credential: Any) -> None:
        self.workspace_id = workspace_id
        self.credential = credential

    def write_back_rules(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Convert rules to KQL analytics rules; echo for demo
        return {"status": "ok", "count": len(rules)}


class OpenSearchConnector:
    def __init__(self, endpoint: str, auth: Any) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.auth = auth

    def write_back_rules(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Convert rules to Detector rules in Security Analytics; echo for demo
        return {"status": "ok", "count": len(rules)}
