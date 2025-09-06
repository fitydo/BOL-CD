"""
Decision Engine with Integrated False Suppression Validation
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from src.bolcd.condense.policy import (
    ROOT_PASS, ALLOWLIST, within_near_window, strong_edge, 
    POLICY_VERSION, should_always_pass, calculate_suppression_confidence,
    FALSE_SUPPRESSION_THRESHOLD
)
from src.bolcd.models.condense import (
    Alert, DecisionRecord, Suppressed, ValidationLog
)

def decide_and_record(
    db: Session, 
    alert: Alert, 
    ctx: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Make suppression decision with false suppression validation
    
    ctx: {
      "dag_meta": {"in_deg": {...}},
      "recent_A": { (entity_id, rule_A): last_ts, ... },
      "edge_meta": { (rule_A, rule_B): {"q_value":..., "support":..., "lift":..., "window_sec":3600, "edge_id":"A->B"} }
    }
    """
    
    # Safety checks first
    should_pass, pass_reason = should_always_pass(alert)
    if should_pass:
        return _deliver(db, alert, reason={
            "why": pass_reason,
            "policy_version": POLICY_VERSION
        })
    
    # Root pass policy
    if ROOT_PASS and ctx["dag_meta"].get("in_deg", {}).get(alert.rule_id, 0) == 0:
        return _deliver(db, alert, reason={
            "why": "root_pass",
            "policy_version": POLICY_VERSION
        })
    
    # Find matching edge
    suppress_edge = None
    for (ent, rule_a), ts_a in ctx.get("recent_A", {}).items():
        if ent != alert.entity_id:
            continue
        
        edge_meta = ctx.get("edge_meta", {}).get((rule_a, alert.rule_id))
        if not edge_meta:
            continue
        
        if within_near_window(alert.ts, ts_a) and strong_edge(edge_meta):
            suppress_edge = edge_meta
            break
    
    # No edge found - deliver
    if not suppress_edge:
        return _deliver(db, alert, reason={
            "why": "no_edge",
            "policy_version": POLICY_VERSION
        })
    
    # Validate false suppression risk
    validation_score = _validate_false_suppression(db, alert, suppress_edge)
    
    # Calculate overall confidence
    confidence = calculate_suppression_confidence(alert, suppress_edge, validation_score)
    
    # Make final decision based on validation
    if validation_score > FALSE_SUPPRESSION_THRESHOLD:
        # High false suppression risk - deliver
        return _deliver(db, alert, reason={
            "why": "false_suppression_risk",
            "validation_score": validation_score,
            "confidence": confidence,
            "edge": suppress_edge,
            "policy_version": POLICY_VERSION
        })
    
    # Low risk - suppress
    return _suppress(db, alert, suppress_edge, validation_score, confidence)

def _validate_false_suppression(
    db: Session,
    alert: Alert,
    edge_meta: Dict[str, Any]
) -> float:
    """
    Run false suppression validation
    Returns score 0.0 (safe) to 1.0 (likely false suppression)
    """
    validator = FalseSuppressionValidator()
    
    # Method 1: Severity-based validation
    severity_score = validator.validate_by_severity(alert)
    
    # Method 2: Check for incident correlation
    # Look for recent high-severity events from same entity
    recent_high = db.query(Alert).filter(
        Alert.entity_id == alert.entity_id,
        Alert.severity.in_(["high", "critical"]),
        Alert.ts >= datetime.now(timezone.utc) - timedelta(hours=1),
        Alert.id != alert.id
    ).count()
    
    correlation_score = min(recent_high * 0.2, 1.0)  # Each recent high event adds 0.2
    
    # Method 3: Statistical anomaly
    # Check if this is a rare event
    same_pattern_count = db.query(Alert).filter(
        Alert.entity_id == alert.entity_id,
        Alert.rule_id == alert.rule_id,
        Alert.ts >= datetime.now(timezone.utc) - timedelta(days=7)
    ).count()
    
    rarity_score = 1.0 / (same_pattern_count + 1)  # Rarer = higher score
    
    # Combine scores with weights
    weights = {
        "severity": 0.4,
        "correlation": 0.3,
        "rarity": 0.3
    }
    
    final_score = (
        severity_score * weights["severity"] +
        correlation_score * weights["correlation"] +
        rarity_score * weights["rarity"]
    )
    
    # Log validation
    validation_log = ValidationLog(
        alert_id=alert.id,
        method="combined",
        score=final_score,
        confidence=0.8,  # Fixed confidence for now
        details={
            "severity_score": severity_score,
            "correlation_score": correlation_score,
            "rarity_score": rarity_score,
            "weights": weights
        }
    )
    db.add(validation_log)
    
    return final_score

def _deliver(db: Session, alert: Alert, reason: Dict[str, Any]) -> Dict[str, Any]:
    """Record delivery decision"""
    # Check if decision already exists
    existing = db.query(DecisionRecord).filter(
        DecisionRecord.alert_id == alert.id
    ).first()
    
    if not existing:
        rec = DecisionRecord(
            alert_id=alert.id,
            decision="deliver",
            confidence=reason.get("confidence", 1.0),
            reason=reason
        )
        db.add(rec)
        db.commit()
    
    return {"decision": "deliver", "reason": reason}

def _suppress(
    db: Session,
    alert: Alert,
    edge_meta: Dict[str, Any],
    validation_score: float,
    confidence: float
) -> Dict[str, Any]:
    """Record suppression decision"""
    reason = {
        "why": "edge",
        "validation_score": validation_score,
        "confidence": confidence,
        "policy_version": POLICY_VERSION,
        **edge_meta
    }
    
    # Check if decision already exists
    existing = db.query(DecisionRecord).filter(
        DecisionRecord.alert_id == alert.id
    ).first()
    
    if not existing:
        rec = DecisionRecord(
            alert_id=alert.id,
            decision="suppress",
            confidence=confidence,
            reason=reason
        )
        db.add(rec)
        
        sup = Suppressed(
            alert_id=alert.id,
            edge_id=edge_meta.get("edge_id"),
            false_suppression_score=validation_score,
            validation_method="combined",
            validation_details={
                "confidence": confidence,
                "edge_q": edge_meta.get("q_value")
            },
            meta={"q": edge_meta.get("q_value")}
        )
        db.add(sup)
        db.commit()
    
    return {"decision": "suppress", "reason": reason}

from datetime import timedelta

class FalseSuppressionValidator:
    """Simplified inline validator"""
    
    def validate_by_severity(self, alert: Alert) -> float:
        """Severity-based validation"""
        severity_scores = {
            "critical": 0.9,
            "high": 0.7,
            "medium": 0.3,
            "low": 0.1,
            "info": 0.0
        }
        return severity_scores.get(alert.severity, 0.5)
