"""
Late Replay Reconciliation Job
Identifies suppressed alerts that should be delivered late
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
import os
import logging

from src.bolcd.db import SessionLocal
from src.bolcd.models.condense import Suppressed, LateReplay, Alert, ValidationLog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TTL_SEC = int(os.getenv("BOLCD_LATE_TTL_SEC", "86400"))  # 24 hours default
DRIFT_THRESHOLD = float(os.getenv("BOLCD_DRIFT_THRESHOLD", "0.5"))
FALSE_SUPPRESSION_THRESHOLD = float(os.getenv("BOLCD_LATE_FALSE_THRESHOLD", "0.6"))

def edge_drifted(edge_meta: dict) -> bool:
    """
    Check if edge has drifted from original learning
    TODO: Implement actual drift detection based on recent performance
    """
    if not edge_meta:
        return False
    
    # Check if q-value has increased significantly
    original_q = edge_meta.get("original_q", 0.05)
    current_q = edge_meta.get("current_q", original_q)
    
    if current_q > original_q * 2:  # Q-value doubled = significant drift
        return True
    
    # Check if support has dropped
    original_support = edge_meta.get("original_support", 20)
    current_support = edge_meta.get("current_support", original_support)
    
    if current_support < original_support * 0.5:  # Support halved
        return True
    
    return False

def should_late_replay(sup: Suppressed, db: Session) -> tuple[bool, str, float]:
    """
    Determine if suppressed alert should be late-replayed
    Returns (should_replay, reason, confidence)
    """
    
    # Check 1: TTL Policy - old suppressions should be reviewed
    age_seconds = (datetime.now(timezone.utc) - sup.inserted_ts).total_seconds()
    if age_seconds >= TTL_SEC:
        return True, "ttl_policy", 0.7
    
    # Check 2: High false suppression score
    if sup.false_suppression_score and sup.false_suppression_score >= FALSE_SUPPRESSION_THRESHOLD:
        return True, "false_suppression", sup.false_suppression_score
    
    # Check 3: Edge drift detection
    meta = sup.meta or {}
    if edge_drifted(meta):
        return True, "edge_drift", 0.6
    
    # Check 4: Severity escalation
    # If similar alerts from same entity are now high severity
    alert = sup.alert
    if alert:
        recent_high = db.query(Alert).filter(
            and_(
                Alert.entity_id == alert.entity_id,
                Alert.rule_id == alert.rule_id,
                Alert.severity.in_(["high", "critical"]),
                Alert.ts > sup.inserted_ts
            )
        ).count()
        
        if recent_high > 0:
            return True, "severity_escalation", 0.8
    
    # Check 5: Manual override or validation update
    recent_validation = db.query(ValidationLog).filter(
        and_(
            ValidationLog.alert_id == sup.alert_id,
            ValidationLog.validation_ts > sup.inserted_ts,
            ValidationLog.score > 0.7
        )
    ).first()
    
    if recent_validation:
        return True, "validation_update", recent_validation.score
    
    return False, "", 0.0

def run_once():
    """
    Run one reconciliation cycle
    """
    db: Session = SessionLocal()
    try:
        logger.info("Starting late replay reconciliation...")
        
        # Fetch pending suppressed alerts
        pending = db.query(Suppressed).filter(
            Suppressed.status == "pending"
        ).all()
        
        logger.info(f"Found {len(pending)} pending suppressed alerts")
        
        late_count = 0
        for sup in pending:
            should_replay, reason, confidence = should_late_replay(sup, db)
            
            if not should_replay:
                # Check if it should expire instead
                age_seconds = (datetime.now(timezone.utc) - sup.inserted_ts).total_seconds()
                if age_seconds > TTL_SEC * 2:  # Double TTL = expire
                    sup.status = "expired"
                    logger.debug(f"Expired suppressed alert {sup.alert_id}")
                continue
            
            # Fetch the alert
            alert = db.query(Alert).filter(Alert.id == sup.alert_id).first()
            if not alert:
                logger.warning(f"Alert {sup.alert_id} not found for late replay")
                continue
            
            # Check if already in late replay
            existing = db.query(LateReplay).filter(
                LateReplay.alert_id == alert.id
            ).first()
            
            if existing:
                logger.debug(f"Alert {alert.id} already in late replay")
                continue
            
            # Create late replay entry
            late_replay = LateReplay(
                alert_id=alert.id,
                original_ts=alert.ts,
                reason=reason,
                confidence=confidence,
                delivered=False
            )
            db.add(late_replay)
            
            # Update suppressed status
            sup.status = "late"
            
            late_count += 1
            logger.info(f"Added alert {alert.id} to late replay (reason: {reason}, confidence: {confidence:.2f})")
        
        # Commit all changes
        db.commit()
        logger.info(f"Reconciliation complete. Added {late_count} alerts to late replay")
        
        # Clean up old expired entries (optional)
        expired_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        expired_count = db.query(Suppressed).filter(
            and_(
                Suppressed.status == "expired",
                Suppressed.inserted_ts < expired_cutoff
            )
        ).delete()
        
        if expired_count > 0:
            db.commit()
            logger.info(f"Cleaned up {expired_count} expired suppressions")
            
    except Exception as e:
        logger.error(f"Reconciliation error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def run_continuous(interval_seconds: int = 300):
    """
    Run reconciliation continuously
    """
    import time
    
    logger.info(f"Starting continuous reconciliation (interval: {interval_seconds}s)")
    
    while True:
        try:
            run_once()
        except Exception as e:
            logger.error(f"Reconciliation cycle failed: {e}")
        
        time.sleep(interval_seconds)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Late Replay Reconciler")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=300, help="Interval in seconds for continuous mode")
    args = parser.parse_args()
    
    if args.once:
        run_once()
    else:
        run_continuous(args.interval)
