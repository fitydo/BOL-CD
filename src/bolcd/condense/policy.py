"""
Alert Suppression Policy with Safety Guards
"""
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Policy parameters from environment
# NOTE: Align with ADR-0002 (FDR Benjamini–Hochberg) default q=0.01
ALPHA = float(os.getenv("BOLCD_POLICY_ALPHA", "0.01"))
S_MIN = int(os.getenv("BOLCD_POLICY_SUPPORT_MIN", "20"))
LIFT_MIN = float(os.getenv("BOLCD_POLICY_LIFT_MIN", "1.5"))
NEAR_SEC = int(os.getenv("BOLCD_NEAR_WINDOW_SEC", "3600"))
ROOT_PASS = os.getenv("BOLCD_ROOT_PASS", "true").lower() == "true"
ALLOWLIST = {r.strip() for r in os.getenv("BOLCD_ALLOWLIST_RULES", "").split(",") if r.strip()}
POLICY_VERSION = os.getenv("BOLCD_POLICY_VERSION", "safe-1.0.0")

# False suppression thresholds
FALSE_SUPPRESSION_THRESHOLD = float(os.getenv("BOLCD_FALSE_SUPPRESSION_THRESHOLD", "0.3"))
HIGH_SEVERITY_PROTECTION = os.getenv("BOLCD_HIGH_SEVERITY_PROTECTION", "true").lower() == "true"

def is_root(rule_id: str, dag_meta: Dict[str, Any]) -> bool:
    """Check if rule is a root node (no incoming edges)"""
    in_degrees = dag_meta.get("in_deg", {})
    return in_degrees.get(rule_id, 0) == 0

def within_near_window(alert_ts: datetime, reference_ts: datetime) -> bool:
    """Check if alert is within near time window"""
    delta_seconds = (alert_ts - reference_ts).total_seconds()
    return 0 <= delta_seconds <= NEAR_SEC

def strong_edge(edge_meta: Dict[str, Any]) -> bool:
    """Check if edge meets strength criteria"""
    return (
        edge_meta.get("q_value", 1.0) <= ALPHA and
        edge_meta.get("support", 0) >= S_MIN and
        edge_meta.get("lift", 1.0) >= LIFT_MIN
    )

def should_always_pass(alert: Any) -> tuple[bool, Optional[str]]:
    """
    Check if alert should always pass (never suppress)
    Returns (should_pass, reason)
    """
    # High/Critical severity protection
    if HIGH_SEVERITY_PROTECTION and alert.severity in ["high", "critical"]:
        return True, "high_severity_protection"
    
    # Allowlist rules
    if alert.rule_id in ALLOWLIST:
        return True, "allowlist"
    
    # Security-critical signatures
    critical_signatures = {
        "privilege_escalation", "data_exfiltration", "malware_detected",
        "unauthorized_access", "sql_injection", "command_injection",
        "ransomware", "backdoor", "rootkit"
    }
    
    if alert.signature and any(
        crit in alert.signature.lower() 
        for crit in critical_signatures
    ):
        return True, "critical_signature"
    
    return False, None

def calculate_suppression_confidence(
    alert: Any,
    edge_meta: Dict[str, Any],
    validation_score: float = 0.0
) -> float:
    """
    Calculate confidence score for suppression decision
    Higher score = more confident to suppress
    """
    base_confidence = 1.0
    
    # Reduce confidence for high severity
    severity_weights = {
        "critical": 0.1,
        "high": 0.3,
        "medium": 0.7,
        "low": 1.0,
        "info": 1.0
    }
    base_confidence *= severity_weights.get(alert.severity, 0.5)
    
    # Edge strength contribution
    if edge_meta:
        q_value = edge_meta.get("q_value", 1.0)
        support = edge_meta.get("support", 0)
        lift = edge_meta.get("lift", 1.0)
        
        # Lower q-value = higher confidence
        q_confidence = 1.0 - min(q_value, 1.0)
        
        # Higher support = higher confidence
        support_confidence = min(support / (S_MIN * 2), 1.0)
        
        # Higher lift = higher confidence
        lift_confidence = min(lift / (LIFT_MIN * 2), 1.0)
        
        edge_confidence = (q_confidence + support_confidence + lift_confidence) / 3
        base_confidence *= edge_confidence
    
    # Reduce confidence based on false suppression risk
    if validation_score > 0:
        base_confidence *= (1.0 - validation_score)
    
    return max(0.0, min(1.0, base_confidence))
