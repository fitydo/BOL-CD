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


def normalize_event_to_logical(ev: Dict[str, Any]) -> Dict[str, Any]:
    """Map common OCSF/ECS fields into a logical schema used by the core."""
    out: Dict[str, Any] = {}
    # Timestamps
    out["ts"] = ev.get("time") or ev.get("@timestamp") or ev.get("timestamp")
    # Network
    out["src_ip"] = ev.get("src_endpoint.ip") or ev.get("source.ip")
    out["dst_ip"] = ev.get("dst_endpoint.ip") or ev.get("destination.ip")
    # Principal/process
    out["user"] = ev.get("user.name") or ev.get("user")
    out["process"] = ev.get("process.name") or ev.get("process")
    # Action
    out["action"] = ev.get("activity_id") or ev.get("event.action") or ev.get("action")
    # Technique
    out["technique"] = (
        ev.get("attack.technique_id") or ev.get("threat.technique.id") or ev.get("technique")
    )
    return out


