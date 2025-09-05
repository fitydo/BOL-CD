"""
Tests for Condensed Alert API
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.bolcd.api.main import app
from src.bolcd.db import get_db
from src.bolcd.models.condense import Base, Alert, DecisionRecord, Suppressed

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)

# Test API key
TEST_API_KEY = "demo-key-admin"

@pytest.fixture(autouse=True)
def setup_database():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_ingest_alert():
    """Test alert ingestion"""
    alert_data = {
        "ts": datetime.utcnow().isoformat(),
        "entity_id": "test-host",
        "rule_id": "TEST-001",
        "severity": "medium",
        "signature": "test_alert"
    }
    
    response = client.post(
        "/v1/ingest",
        json=alert_data,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["alert_id"] is not None
    assert data["decision"] in ["deliver", "suppress"]

def test_list_alerts_condensed():
    """Test listing condensed alerts"""
    # First ingest some alerts
    now = datetime.utcnow()
    
    # Alert 1 - will be delivered
    alert1 = {
        "id": "test-1",
        "ts": now.isoformat(),
        "entity_id": "host-1",
        "rule_id": "R-001",
        "severity": "high"
    }
    
    response = client.post(
        "/v1/ingest",
        json=alert1,
        headers={"X-API-Key": TEST_API_KEY}
    )
    assert response.status_code == 200
    
    # Alert 2 - will be suppressed (if R-001 -> R-002 edge exists)
    alert2 = {
        "id": "test-2",
        "ts": (now + timedelta(minutes=5)).isoformat(),
        "entity_id": "host-1",
        "rule_id": "R-002",
        "severity": "low"
    }
    
    response = client.post(
        "/v1/ingest",
        json=alert2,
        headers={"X-API-Key": TEST_API_KEY}
    )
    assert response.status_code == 200
    
    # Get condensed view
    response = client.get(
        "/v1/alerts?view=condensed",
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["view"] == "condensed"

def test_explain_decision():
    """Test decision explanation"""
    # Ingest an alert
    alert_data = {
        "id": "explain-test",
        "ts": datetime.utcnow().isoformat(),
        "entity_id": "test-host",
        "rule_id": "TEST-EXPLAIN",
        "severity": "critical"
    }
    
    response = client.post(
        "/v1/ingest",
        json=alert_data,
        headers={"X-API-Key": TEST_API_KEY}
    )
    assert response.status_code == 200
    
    # Get explanation
    response = client.get(
        "/v1/alerts/explain-test/explain",
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "alert" in data
    assert "decision" in data
    assert data["decision"]["type"] in ["deliver", "suppress"]

def test_api_key_authentication():
    """Test API key authentication"""
    # No API key
    response = client.get("/v1/alerts")
    assert response.status_code == 401
    
    # Invalid API key
    response = client.get(
        "/v1/alerts",
        headers={"X-API-Key": "invalid-key"}
    )
    assert response.status_code == 401
    
    # Valid API key
    response = client.get(
        "/v1/alerts",
        headers={"X-API-Key": TEST_API_KEY}
    )
    assert response.status_code == 200

def test_batch_ingest():
    """Test batch alert ingestion"""
    now = datetime.utcnow()
    
    batch_data = {
        "alerts": [
            {
                "ts": now.isoformat(),
                "entity_id": "host-1",
                "rule_id": "BATCH-001",
                "severity": "low"
            },
            {
                "ts": (now + timedelta(minutes=1)).isoformat(),
                "entity_id": "host-2",
                "rule_id": "BATCH-002",
                "severity": "medium"
            },
            {
                "ts": (now + timedelta(minutes=2)).isoformat(),
                "entity_id": "host-3",
                "rule_id": "BATCH-003",
                "severity": "high"
            }
        ],
        "process": True
    }
    
    response = client.post(
        "/v1/ingest/batch",
        json=batch_data,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["processed"] == 3
    assert data["errors"] == 0

def test_stats_endpoint():
    """Test statistics endpoint"""
    response = client.get(
        "/v1/alerts/stats",
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "totals" in data
    assert "late_replay" in data
    assert "validation" in data

def test_late_replay():
    """Test late replay endpoint"""
    response = client.get(
        "/v1/alerts/late",
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code == 200
    assert "X-Delivered-Late" in response.headers
    data = response.json()
    assert "items" in data
    assert data["meta"]["late_delivery"] is True

def test_delta_view():
    """Test delta view of alerts"""
    response = client.get(
        "/v1/alerts?view=delta",
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["view"] == "delta"
    assert "delivered" in data
    assert "suppressed" in data
    assert "stats" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
