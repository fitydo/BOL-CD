"""
Condensed Alert Data Models with False Suppression Tracking
"""
from datetime import datetime
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey, UniqueConstraint, Float, Text

Base = declarative_base()

class Alert(Base):
    """Original alert from SIEM"""
    __tablename__ = "alerts"
    
    id = Column(String, primary_key=True)                # alert_id（SIEM側IDでも可）
    ts = Column(DateTime, index=True, nullable=False)
    entity_id = Column(String, index=True, nullable=False)
    rule_id = Column(String, index=True, nullable=False)
    severity = Column(String, index=True, nullable=False, default="medium")
    signature = Column(String, index=True, nullable=True)
    attrs = Column(JSON, nullable=True)
    raw_event = Column(Text, nullable=True)  # 元のイベント内容
    
    # Relationships
    decision = relationship("DecisionRecord", back_populates="alert", uselist=False)
    suppressed = relationship("Suppressed", back_populates="alert", uselist=False)
    late_replay = relationship("LateReplay", back_populates="alert", uselist=False)

class DecisionRecord(Base):
    """Decision audit trail"""
    __tablename__ = "decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String, ForeignKey("alerts.id"), index=True, nullable=False, unique=True)
    decision = Column(String, index=True, nullable=False)  # deliver|suppress
    confidence = Column(Float, nullable=True)  # 決定の信頼度
    reason = Column(JSON, nullable=False)  # {edge:{A,B}, q_value, support, window_sec, policy_version, validation_score, ...}
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    alert = relationship("Alert", back_populates="decision")

class Suppressed(Base):
    """Suppressed alerts quarantine"""
    __tablename__ = "suppressed"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String, ForeignKey("alerts.id"), index=True, nullable=False, unique=True)
    edge_id = Column(String, index=True, nullable=True)      # A->B の識別子
    inserted_ts = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, index=True, nullable=False, default="pending")  # pending|late|expired|validated
    
    # 誤抑制検証スコア
    false_suppression_score = Column(Float, nullable=True, default=0.0)
    validation_method = Column(String, nullable=True)  # severity|correlation|statistical|shadow
    validation_details = Column(JSON, nullable=True)
    
    meta = Column(JSON, nullable=True)  # drift scores, edge confidence etc.
    
    # Relationships
    alert = relationship("Alert", back_populates="suppressed")

class LateReplay(Base):
    """Late replayed alerts after validation"""
    __tablename__ = "late_replay"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String, ForeignKey("alerts.id"), index=True, nullable=False, unique=True)
    original_ts = Column(DateTime, index=True, nullable=False)
    late_ts = Column(DateTime, default=datetime.utcnow, index=True)
    reason = Column(String, nullable=False)  # edge_drift|override|severity|ttl_policy|false_suppression
    confidence = Column(Float, nullable=True)  # 遅配判定の信頼度
    delivered = Column(Boolean, default=False)
    
    # Relationships
    alert = relationship("Alert", back_populates="late_replay")

class ValidationLog(Base):
    """False suppression validation history"""
    __tablename__ = "validation_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String, ForeignKey("alerts.id"), index=True, nullable=False)
    validation_ts = Column(DateTime, default=datetime.utcnow, index=True)
    method = Column(String, nullable=False)  # severity|correlation|statistical|shadow|manual
    score = Column(Float, nullable=False)  # 0.0 (safe) to 1.0 (likely false suppression)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    details = Column(JSON, nullable=True)
    
    # Composite index for efficient queries
    __table_args__ = (
        UniqueConstraint('alert_id', 'method', 'validation_ts'),
    )
