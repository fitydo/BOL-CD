"""
Ingest API for Demo and Testing
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import hashlib
import json

from src.bolcd.db import get_db
from src.bolcd.models.condense import Alert
from src.bolcd.auth.api_keys import require_scope
from src.bolcd.condense.engine import decide_and_record
from src.bolcd.metrics.condense_metrics import record_alert, record_decision, observe_duration, decision_latency

router = APIRouter(prefix="/v1/ingest", tags=["ingest"])

class AlertIngest(BaseModel):
    """Alert ingestion model"""
    id: Optional[str] = Field(None, description="Alert ID (auto-generated if not provided)")
    ts: str = Field(..., description="Timestamp in ISO format")
    entity_id: str = Field(..., description="Entity identifier")
    rule_id: str = Field(..., description="Rule identifier")
    severity: str = Field("medium", description="Severity level")
    signature: Optional[str] = Field(None, description="Alert signature")
    attrs: Optional[Dict[str, Any]] = Field(None, description="Additional attributes")
    raw_event: Optional[str] = Field(None, description="Raw event data")

class BatchIngest(BaseModel):
    """Batch alert ingestion"""
    alerts: List[AlertIngest]
    process: bool = Field(True, description="Process decisions immediately")

class IngestResponse(BaseModel):
    """Ingestion response"""
    ok: bool
    alert_id: str
    decision: Optional[str] = None
    reason: Optional[Dict[str, Any]] = None

@router.post("", response_model=IngestResponse)
@observe_duration(decision_latency)
async def ingest_alert(
    alert_data: AlertIngest,
    process: bool = True,
    db: Session = Depends(get_db),
    auth: dict = Depends(require_scope({"admin", "ingest"}))
):
    """
    Ingest a single alert
    For demo/testing purposes - production should use connectors
    """
    
    # Generate ID if not provided
    if not alert_data.id:
        # Create deterministic ID from content
        id_content = f"{alert_data.entity_id}:{alert_data.rule_id}:{alert_data.ts}"
        alert_data.id = hashlib.md5(id_content.encode()).hexdigest()
    
    # Check if alert already exists
    existing = db.query(Alert).filter(Alert.id == alert_data.id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Alert {alert_data.id} already exists"
        )
    
    # Create alert
    alert = Alert(
        id=alert_data.id,
        ts=datetime.fromisoformat(alert_data.ts),
        entity_id=alert_data.entity_id,
        rule_id=alert_data.rule_id,
        severity=alert_data.severity,
        signature=alert_data.signature,
        attrs=alert_data.attrs,
        raw_event=alert_data.raw_event
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    # Record metrics
    record_alert(alert)
    
    # Process decision if requested
    decision_result = None
    if process:
        # Build context for decision
        # In production, this would come from the learning system
        ctx = build_decision_context(db, alert)
        
        # Make decision
        decision_result = decide_and_record(db, alert, ctx)
        
        # Record decision metrics
        record_decision(
            decision_result["decision"],
            decision_result["reason"].get("why", "unknown"),
            alert
        )
    
    return IngestResponse(
        ok=True,
        alert_id=alert.id,
        decision=decision_result["decision"] if decision_result else None,
        reason=decision_result["reason"] if decision_result else None
    )

@router.post("/batch")
async def ingest_batch(
    batch: BatchIngest,
    db: Session = Depends(get_db),
    auth: dict = Depends(require_scope({"admin", "ingest"}))
):
    """
    Ingest multiple alerts in batch
    """
    results = []
    errors = []
    
    for alert_data in batch.alerts:
        try:
            # Generate ID if not provided
            if not alert_data.id:
                id_content = f"{alert_data.entity_id}:{alert_data.rule_id}:{alert_data.ts}"
                alert_data.id = hashlib.md5(id_content.encode()).hexdigest()
            
            # Check if exists
            existing = db.query(Alert).filter(Alert.id == alert_data.id).first()
            if existing:
                errors.append({
                    "alert_id": alert_data.id,
                    "error": "Already exists"
                })
                continue
            
            # Create alert
            alert = Alert(
                id=alert_data.id,
                ts=datetime.fromisoformat(alert_data.ts),
                entity_id=alert_data.entity_id,
                rule_id=alert_data.rule_id,
                severity=alert_data.severity,
                signature=alert_data.signature,
                attrs=alert_data.attrs,
                raw_event=alert_data.raw_event
            )
            
            db.add(alert)
            
            # Process if requested
            decision = None
            if batch.process:
                ctx = build_decision_context(db, alert)
                decision = decide_and_record(db, alert, ctx)
            
            results.append({
                "alert_id": alert.id,
                "decision": decision["decision"] if decision else None
            })
            
        except Exception:
            # Do not leak internal exception details
            errors.append({
                "alert_id": alert_data.id if alert_data.id else "unknown",
                "error": "internal_error"
            })
    
    # Commit all at once
    db.commit()
    
    return {
        "ok": len(errors) == 0,
        "processed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors if errors else None
    }

def build_decision_context(db: Session, alert: Alert) -> Dict[str, Any]:
    """
    Build context for decision making
    In production, this would query the learned DAG and edges
    """
    from datetime import timedelta
    
    # Look for recent alerts from same entity
    recent_window = alert.ts - timedelta(hours=1)
    recent_alerts = db.query(Alert).filter(
        Alert.entity_id == alert.entity_id,
        Alert.ts >= recent_window,
        Alert.ts < alert.ts,
        Alert.id != alert.id
    ).all()
    
    # Build recent_A mapping
    recent_a = {}
    for r_alert in recent_alerts:
        key = (r_alert.entity_id, r_alert.rule_id)
        recent_a[key] = r_alert.ts
    
    # Mock edge metadata (in production, load from learned model)
    edge_meta = {}
    
    # Example: If we see R-001 followed by R-002, suppress R-002
    if ("R-001", "R-002") in [(r.rule_id, alert.rule_id) for r in recent_alerts]:
        edge_meta[("R-001", "R-002")] = {
            "q_value": 0.01,
            "support": 50,
            "lift": 2.5,
            "window_sec": 3600,
            "edge_id": "R-001->R-002"
        }
    
    # Mock DAG metadata
    dag_meta = {
        "in_deg": {
            "R-001": 0,  # Root
            "R-002": 1,  # Has incoming edge
            "R-003": 0,  # Root
        }
    }
    
    return {
        "dag_meta": dag_meta,
        "recent_A": recent_a,
        "edge_meta": edge_meta
    }

@router.get("/sample")
async def get_sample_data():
    """
    Get sample alert data for testing
    """
    now = datetime.utcnow()
    
    samples = [
        {
            "ts": now.isoformat(),
            "entity_id": "host-001",
            "rule_id": "R-001",
            "severity": "medium",
            "signature": "failed_login",
            "attrs": {"user": "admin", "source_ip": "192.168.1.100"}
        },
        {
            "ts": (now + timedelta(minutes=5)).isoformat(),
            "entity_id": "host-001",
            "rule_id": "R-002",
            "severity": "low",
            "signature": "account_locked",
            "attrs": {"user": "admin", "reason": "multiple_failures"}
        },
        {
            "ts": (now + timedelta(minutes=10)).isoformat(),
            "entity_id": "host-002",
            "rule_id": "R-003",
            "severity": "high",
            "signature": "privilege_escalation",
            "attrs": {"user": "user1", "target": "root"}
        }
    ]
    
    return {
        "samples": samples,
        "usage": "POST these to /v1/ingest with your API key"
    }

from datetime import timedelta
