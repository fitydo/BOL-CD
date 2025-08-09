from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class SigmaRule:
    condition: str
    fields: List[str]
    timeframe: str | None = None


def parse_sigma_to_events(rule: Dict[str, Any]) -> SigmaRule:
    # Minimal stub: map keys if exist
    condition = rule.get("condition") or rule.get("detection", {}).get("condition", "")
    fields = sorted(set(rule.get("fields", [])))
    timeframe = rule.get("timeframe")
    return SigmaRule(condition=condition, fields=fields, timeframe=timeframe)
