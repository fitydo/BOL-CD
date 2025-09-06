"""
Condensed Alert API with Late Replay Support
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from src.bolcd.db import get_db
from src.bolcd.models.condense import Alert, DecisionRecord, Suppressed, LateReplay, ValidationLog
from src.bolcd.auth.api_keys import require_scope, get_current_scope

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])

class AlertResponse(BaseModel):
    id: str
    ts: str
    entity_id: str
    rule_id: str
    severity: str
    signature: Optional[str] = None
    attrs: Optional[Dict[str, Any]] = None

class DecisionResponse(BaseModel):
    alert: AlertResponse
    decision: str
    confidence: float
    reason: Dict[str, Any]
    
class LateReplayResponse(BaseModel):
    alert: AlertResponse
    original_ts: str
    late_ts: str
    reason: str
    confidence: Optional[float] = None

def serialize_alert(alert: Alert) -> dict:
    """Serialize Alert model to dict"""
    return {
        "id": alert.id,
        "ts": alert.ts.isoformat(),
        "entity_id": alert.entity_id,
        "rule_id": alert.rule_id,
        "severity": alert.severity,
        "signature": alert.signature,
        "attrs": alert.attrs
    }

@router.get("")
def list_alerts(
    view: str = Query("condensed", pattern="^(condensed|full|delta)$"),
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    severity: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    auth: dict = Depends(get_current_scope)
):
    """
    List alerts based on view type
    - condensed: Only delivered alerts (post-suppression)
    - full: All alerts (delivered + suppressed)
    - delta: Alert IDs by decision type
    """
    
    # Authorization by view
    scope = auth.get("scope")
    if view == "full" and scope not in {"admin", "full"}:
        raise HTTPException(status_code=403, detail="Full view requires admin/full scope")
    if view in {"condensed", "delta"} and scope not in {"condensed", "admin", "full", "delta"}:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Base query for decisions
    q_dec = db.query(DecisionRecord)
    
    # Time filters
    if since:
        q_dec = q_dec.filter(DecisionRecord.created_at >= since)
    if until:
        q_dec = q_dec.filter(DecisionRecord.created_at <= until)
    
    # Get alert IDs based on view
    if view == "condensed":
        decisions = q_dec.filter(DecisionRecord.decision == "deliver").limit(limit).offset(offset).all()
        alert_ids = [d.alert_id for d in decisions]
    elif view == "full":
        decisions = q_dec.limit(limit).offset(offset).all()
        alert_ids = [d.alert_id for d in decisions]
    else:  # delta
        delivered = [d.alert_id for d in q_dec.filter(DecisionRecord.decision == "deliver").all()]
        suppressed = [d.alert_id for d in q_dec.filter(DecisionRecord.decision == "suppress").all()]
        
        return {
            "view": "delta",
            "delivered": delivered[:limit],
            "suppressed": suppressed[:limit],
            "stats": {
                "total_delivered": len(delivered),
                "total_suppressed": len(suppressed),
                "suppression_rate": len(suppressed) / (len(delivered) + len(suppressed)) if (delivered or suppressed) else 0
            }
        }
    
    # Fetch alerts
    q_alerts = db.query(Alert).filter(Alert.id.in_(alert_ids))
    
    # Additional filters
    if severity:
        q_alerts = q_alerts.filter(Alert.severity == severity)
    if entity_id:
        q_alerts = q_alerts.filter(Alert.entity_id == entity_id)
    
    alerts = q_alerts.all()
    serialized = [serialize_alert(a) for a in alerts]

    return {
        "view": view,
        "count": len(alerts),
        "items": serialized,
        # Backward-compat: some clients expect "alerts"
        "alerts": serialized,
        "meta": {
            "limit": limit,
            "offset": offset,
            "scope": auth["scope"]
        }
    }

@router.get("/late")
def list_late_replay(
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    delivered: Optional[bool] = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    auth: dict = Depends(require_scope({"condensed", "full", "admin"}))
):
    """
    List late-replayed alerts
    These are alerts initially suppressed but later determined to be important
    """
    q = db.query(LateReplay).join(Alert)
    
    if since:
        q = q.filter(LateReplay.late_ts >= since)
    if until:
        q = q.filter(LateReplay.late_ts <= until)
    if delivered is not None:
        q = q.filter(LateReplay.delivered == delivered)
    
    items = q.limit(limit).all()
    
    response_items = []
    for item in items:
        response_items.append({
            "alert": serialize_alert(item.alert),
            "original_ts": item.original_ts.isoformat(),
            "late_ts": item.late_ts.isoformat(),
            "reason": item.reason,
            "confidence": item.confidence,
            "delivered": item.delivered
        })
    
    # Set header to indicate late delivery and return JSON
    payload = {
        "count": len(response_items),
        "items": response_items,
        "meta": {
            "late_delivery": True,
            "scope": auth["scope"]
        }
    }
    return JSONResponse(content=payload, headers={"X-Delivered-Late": "true"})

@router.get("/{alert_id}/explain")
def explain_decision(
    alert_id: str,
    db: Session = Depends(get_db),
    auth: dict = Depends(require_scope({"condensed", "full", "admin"}))
):
    """
    Explain the decision made for a specific alert
    Provides full audit trail and reasoning
    """
    
    # Fetch alert
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Fetch decision
    decision = db.query(DecisionRecord).filter(DecisionRecord.alert_id == alert_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="No decision found for alert")
    
    # Fetch suppression details if suppressed
    suppressed = None
    if decision.decision == "suppress":
        suppressed = db.query(Suppressed).filter(Suppressed.alert_id == alert_id).first()
    
    # Fetch late replay if exists
    late_replay = db.query(LateReplay).filter(LateReplay.alert_id == alert_id).first()
    
    # Fetch validation logs
    validations = db.query(ValidationLog).filter(
        ValidationLog.alert_id == alert_id
    ).order_by(ValidationLog.validation_ts.desc()).all()
    
    response = {
        "alert": serialize_alert(alert),
        "decision": {
            "type": decision.decision,
            "confidence": decision.confidence,
            "reason": decision.reason,
            "created_at": decision.created_at.isoformat()
        }
    }
    
    # Add suppression details if applicable
    if suppressed:
        response["suppression"] = {
            "edge_id": suppressed.edge_id,
            "status": suppressed.status,
            "false_suppression_score": suppressed.false_suppression_score,
            "validation_method": suppressed.validation_method,
            "validation_details": suppressed.validation_details
        }
    
    # Add late replay info if applicable
    if late_replay:
        response["late_replay"] = {
            "original_ts": late_replay.original_ts.isoformat(),
            "late_ts": late_replay.late_ts.isoformat(),
            "reason": late_replay.reason,
            "confidence": late_replay.confidence,
            "delivered": late_replay.delivered
        }
    
    # Add validation history
    if validations:
        response["validations"] = [
            {
                "method": v.method,
                "score": v.score,
                "confidence": v.confidence,
                "timestamp": v.validation_ts.isoformat(),
                "details": v.details
            }
            for v in validations
        ]
    
    # Add response headers
    headers = {
        "X-Policy-Version": decision.reason.get("policy_version", "unknown"),
        "X-Decision-Confidence": str(decision.confidence)
    }
    
    if suppressed and suppressed.edge_id:
        headers["X-Edge-Id"] = suppressed.edge_id
        headers["X-Q-Value"] = str(decision.reason.get("q_value", ""))
    
    return JSONResponse(content=response, headers=headers)

@router.get("/stats")
def get_statistics(
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    db: Session = Depends(get_db),
    auth: dict = Depends(get_current_scope)
):
    """
    Get alert statistics
    """
    q_alerts = db.query(Alert)
    q_decisions = db.query(DecisionRecord)
    
    if since:
        q_alerts = q_alerts.filter(Alert.ts >= since)
        q_decisions = q_decisions.filter(DecisionRecord.created_at >= since)
    if until:
        q_alerts = q_alerts.filter(Alert.ts <= until)
        q_decisions = q_decisions.filter(DecisionRecord.created_at <= until)
    
    total_alerts = q_alerts.count()
    delivered = q_decisions.filter(DecisionRecord.decision == "deliver").count()
    suppressed = q_decisions.filter(DecisionRecord.decision == "suppress").count()
    
    # Late replay stats
    late_total = db.query(LateReplay).count()
    late_delivered = db.query(LateReplay).filter(LateReplay.delivered == True).count()
    
    # False suppression stats
    high_risk = db.query(Suppressed).filter(
        Suppressed.false_suppression_score > 0.5
    ).count()
    
    return {
        "period": {
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None
        },
        "totals": {
            "alerts": total_alerts,
            "delivered": delivered,
            "suppressed": suppressed,
            "suppression_rate": suppressed / (delivered + suppressed) if (delivered + suppressed) > 0 else 0
        },
        "late_replay": {
            "total": late_total,
            "delivered": late_delivered,
            "pending": late_total - late_delivered
        },
        "validation": {
            "high_risk_suppressions": high_risk,
            "risk_rate": high_risk / suppressed if suppressed > 0 else 0
        },
        "meta": {
            "scope": auth["scope"]
        }
    }
