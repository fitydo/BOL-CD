from __future__ import annotations

from typing import Any, Dict


def normalize_to_ocsf(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal normalizer to an OCSF/ECS-like schema used in docs.
    Maps common SIEM fields to a canonical set used by binarizer thresholds.
    This is a placeholder and not a full OCSF/ECS implementation.
    """
    out: Dict[str, Any] = dict(event)
    # Common renames
    if "host" not in out and "host_name" in out:
        out["host"] = out.pop("host_name")
    if "user" not in out and "user_name" in out:
        out["user"] = out.pop("user_name")
    if "process" not in out and "process_name" in out:
        out["process"] = out.pop("process_name")
    # Flatten nested dicts that often appear
    asset = out.get("asset")
    if isinstance(asset, dict):
        for k, v in asset.items():
            out[f"asset.{k}"] = v
    return out


